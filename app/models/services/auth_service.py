import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app, request
from flask_mail import Message
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, mail
from app.models.admin_account import AdminAccount
from app.models.history import AuthAuditLog, PasswordHistory, SecurityAlert
from app.models.user import User


def validate_password_policy(password):
    """Enforce min length and at least 3/4 character classes."""
    if len(password or "") < 8:
        return False, "password must be at least 8 characters"

    checks = [
        bool(re.search(r"[A-Z]", password)),
        bool(re.search(r"[a-z]", password)),
        bool(re.search(r"\d", password)),
        bool(re.search(r"[^A-Za-z0-9]", password)),
    ]

    if sum(checks) < 3:
        return (
            False,
            "password must contain at least 3 of: uppercase, lowercase, number, special",
        )

    return True, None


def record_auth_event(actor_type, actor_id, event_type, success, reason=None):
    """Persist auth event with request metadata for audit queries."""
    session_cookie = request.cookies.get("session")
    user_agent = request.headers.get("User-Agent", "")

    event = AuthAuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        session_id=session_cookie,
        user_agent=user_agent[:255],
        success=bool(success),
        reason=(reason or "")[:255] or None,
    )
    db.session.add(event)


def maybe_raise_suspicious_alert(actor_type, actor_id):
    """Create alert and apply auto-lock when failures exceed threshold window."""
    if actor_id is None:
        return

    now = datetime.utcnow()
    window_minutes = max(1, int(current_app.config.get("SUSPICIOUS_WINDOW_MINUTES", 10)))
    threshold = max(3, int(current_app.config.get("SUSPICIOUS_FAILED_ATTEMPTS", 5)))
    window_start = now - timedelta(minutes=window_minutes)

    failed_count = (
        AuthAuditLog.query.filter(
            AuthAuditLog.actor_type == actor_type,
            AuthAuditLog.actor_id == actor_id,
            AuthAuditLog.success.is_(False),
            AuthAuditLog.event_type.in_(["login", "api_login"]),
            AuthAuditLog.created_at >= window_start,
        )
        .count()
    )

    if failed_count < threshold:
        return

    existing = (
        SecurityAlert.query.filter_by(
            actor_type=actor_type,
            actor_id=actor_id,
            alert_type="bruteforce_login",
            resolved=False,
        )
        .order_by(SecurityAlert.created_at.desc())
        .first()
    )
    if existing is not None:
        return

    lock_until = now + timedelta(minutes=15)
    target = AdminAccount.query.get(actor_id) if actor_type == "admin" else User.query.get(actor_id)
    if target is not None:
        target.lockout_until = lock_until

    db.session.add(
        SecurityAlert(
            actor_type=actor_type,
            actor_id=actor_id,
            alert_type="bruteforce_login",
            severity="high",
            reason=f"{failed_count} failed logins in {window_minutes} minutes",
            auto_action="temporary_lock_15m",
        )
    )


def _password_history_limit():
    return max(1, int(current_app.config.get("PASSWORD_HISTORY_COUNT", 5)))


def is_password_reused(account_type, account_id, new_password, current_password_hash=None):
    """Check candidate password against current and recent password hashes."""
    if current_password_hash and check_password_hash(current_password_hash, new_password):
        return True

    history = (
        PasswordHistory.query.filter_by(account_type=account_type, account_id=account_id)
        .order_by(PasswordHistory.created_at.desc(), PasswordHistory.id.desc())
        .limit(_password_history_limit())
        .all()
    )
    return any(check_password_hash(item.password_hash, new_password) for item in history)


def store_password_history(account_type, account_id, password_hash):
    """Persist latest password hash and keep only configured history count."""
    db.session.add(
        PasswordHistory(
            account_type=account_type,
            account_id=account_id,
            password_hash=password_hash,
        )
    )

    keep = _password_history_limit()
    old_rows = (
        PasswordHistory.query.filter_by(account_type=account_type, account_id=account_id)
        .order_by(PasswordHistory.created_at.desc(), PasswordHistory.id.desc())
        .offset(keep)
        .all()
    )
    for row in old_rows:
        db.session.delete(row)


def generate_admin_jwt(admin):
    """Generate short-lived JWT token for API-only authentication."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=max(1, int(current_app.config.get("JWT_EXPIRATION_MINUTES", 60))))
    payload = {
        "sub": f"admin:{admin.id}",
        "type": "admin",
        "username": admin.username,
        "sv": int(admin.session_version or 1),
        "auth_level": int(admin.session_auth_level or 1),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, current_app.config.get("JWT_SECRET_KEY"), algorithm="HS256")
    return token, exp


def get_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def get_admin_from_jwt(token):
    """Decode JWT and return associated admin account when valid."""
    try:
        payload = jwt.decode(
            token,
            current_app.config.get("JWT_SECRET_KEY"),
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        return None, "token expired", 401
    except jwt.InvalidTokenError:
        return None, "invalid token", 401

    if payload.get("type") != "admin":
        return None, "invalid token subject", 401

    sub = str(payload.get("sub", ""))
    if not sub.startswith("admin:"):
        return None, "invalid token subject", 401

    admin_id = sub.split(":", 1)[1]
    if not admin_id.isdigit():
        return None, "invalid token subject", 401

    admin = AdminAccount.query.get(int(admin_id))
    if admin is None or not admin.is_active:
        return None, "account is inactive", 403

    token_sv = int(payload.get("sv", 0) or 0)
    if token_sv != int(admin.session_version or 1):
        return None, "token revoked", 401

    return admin, None, None


def set_session_auth_level(user, level):
    user.session_auth_level = int(max(1, min(4, level)))


def setup_security_question(user, question, answer):
    user.security_question = (question or "").strip()[:255] or None
    if answer:
        user.set_security_answer(answer)


def generate_otp_code(user):
    code = f"{secrets.randbelow(1000000):06d}"
    user.otp_code_hash = generate_password_hash(code)
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
    return code


def verify_otp_code(user, code):
    if not user.otp_code_hash or not user.otp_expires_at:
        return False
    if user.otp_expires_at < datetime.utcnow():
        return False
    return check_password_hash(user.otp_code_hash, code or "")


def clear_otp_code(user):
    user.otp_code_hash = None
    user.otp_expires_at = None


def send_otp_challenge(user, actor_type):
    code = generate_otp_code(user)
    destination = None
    method = getattr(user, "mfa_method", "totp")

    if method == "email_otp":
        destination = getattr(user, "email", None) or getattr(user, "personal_email", None)
        if destination:
            msg = Message(
                "Your IAM verification code",
                recipients=[destination],
                body=f"Your verification code is: {code}",
            )
            mail.send(msg)
    elif method == "sms_otp":
        destination = getattr(user, "phone_number", None)

    record_auth_event(actor_type, user.id, "mfa_otp_sent", True, f"method={method}")
    return code, method, destination


def validate_active_session(user, session_payload):
    """Validate idle timeout, absolute timeout, and revocation version."""
    if user is None:
        return False, "invalid session"

    session_version = int(session_payload.get("session_version", 0) or 0)
    if session_version != int(user.session_version or 1):
        return False, "session revoked"

    now = datetime.utcnow()
    idle_limit = timedelta(minutes=max(1, int(current_app.config.get("SESSION_IDLE_TIMEOUT_MINUTES", 20))))
    absolute_limit = timedelta(minutes=max(1, int(current_app.config.get("SESSION_ABSOLUTE_TIMEOUT_MINUTES", 480))))

    issued_at_raw = session_payload.get("issued_at")
    last_seen_raw = session_payload.get("last_seen")
    if not issued_at_raw or not last_seen_raw:
        return False, "invalid session timestamps"

    issued_at = datetime.fromisoformat(issued_at_raw)
    last_seen = datetime.fromisoformat(last_seen_raw)
    if now - last_seen > idle_limit:
        return False, "session idle timeout"
    if now - issued_at > absolute_limit:
        return False, "session expired"

    session_payload["last_seen"] = now.isoformat()
    return True, None

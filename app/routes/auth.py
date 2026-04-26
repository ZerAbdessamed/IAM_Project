from flask import current_app, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import login_user, logout_user, login_required, current_user
from app.models import AdminAccount
from app.models.user import User
from app.routes import auth_bp
from app import db, mail
from flask_mail import Message
import qrcode
import io
from datetime import datetime, timedelta
import json
import os



LOG_FILE = "logs/auth_log.json"
SECURITY_RECOVERY_SESSION_KEY = "security_recovery_ctx"
SECURITY_QUESTION_CHOICES = [
    ("first_pet", "What was the name of your first pet?"),
    ("childhood_street", "What is the name of the street you grew up on?"),
    ("first_school", "What was the name of your first school?"),
    ("favorite_teacher", "What was the last name of your favorite teacher?"),
    ("first_job_city", "In what city did you have your first job?"),
    ("childhood_nickname", "What was your childhood nickname?"),
]
SECURITY_QUESTION_MAP = dict(SECURITY_QUESTION_CHOICES)


def get_email(user):
    return getattr(user, "personal_email", None) or getattr(user, "email", "unknown")


def write_log(username, action, status, log_type="login"):
    os.makedirs("logs", exist_ok=True)

    log_entry = {
        "username": username,
        "action": action,
        "status": status,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "type": log_type
    }

    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = []
    else:
        data = []

    data.append(log_entry)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def _redirect_for_user_type(user_type):
    if user_type == "admin":
        return redirect(url_for("admin.admin_dashboard"))
    if user_type == "student":
        return redirect(url_for("main.student_profile"))
    return redirect(url_for("main.staff_profile"))


def _get_security_recovery_config():
    return {
        "max_attempts": max(
            1,
            int(current_app.config.get("SECURITY_RECOVERY_MAX_ATTEMPTS", 5)),
        ),
        "lockout_minutes": max(
            1,
            int(current_app.config.get("SECURITY_RECOVERY_LOCKOUT_MINUTES", 15)),
        ),
        "challenge_ttl_minutes": max(
            1,
            int(current_app.config.get("SECURITY_RECOVERY_CHALLENGE_TTL_MINUTES", 10)),
        ),
    }


def _security_question_label(question_key):
    return SECURITY_QUESTION_MAP.get(question_key, question_key or "")


def _mask_email(email):
    email = str(email or "").strip()
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        local_mask = local[:1] + "*"
    else:
        local_mask = local[:2] + "*" * (len(local) - 2)
    return f"{local_mask}@{domain}"


def _start_security_recovery_session(user_id):
    session[SECURITY_RECOVERY_SESSION_KEY] = {
        "user_id": int(user_id),
        "issued_at": datetime.utcnow().isoformat(),
    }


def _clear_security_recovery_session():
    session.pop(SECURITY_RECOVERY_SESSION_KEY, None)


def _load_security_recovery_user():
    payload = session.get(SECURITY_RECOVERY_SESSION_KEY)
    if not isinstance(payload, dict):
        return None, None

    issued_at_raw = payload.get("issued_at")
    user_id = payload.get("user_id")
    if issued_at_raw is None or user_id is None:
        _clear_security_recovery_session()
        return None, "invalid"

    try:
        issued_at = datetime.fromisoformat(str(issued_at_raw))
        user_id = int(user_id)
    except (TypeError, ValueError):
        _clear_security_recovery_session()
        return None, "invalid"

    challenge_ttl = _get_security_recovery_config()["challenge_ttl_minutes"]
    if datetime.utcnow() - issued_at > timedelta(minutes=challenge_ttl):
        _clear_security_recovery_session()
        return None, "expired"

    user = User.query.get(user_id)
    if user is None or not user.has_security_question:
        _clear_security_recovery_session()
        return None, "invalid"

    return user, None



@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        logout_user()
        session.clear()

    if request.method == 'POST':

        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user_type = request.form.get('user_type')

        user = None

        # ---------------- FIND USER ----------------
        if user_type == "admin":
            user = AdminAccount.query.filter(
                (AdminAccount.username == username) |
                (AdminAccount.email == username)
            ).first()
        else:
            user = User.query.filter(
                (User.personal_email == username) &
                (User.user_type == user_type)
            ).first()

        if not user:
            write_log(username, "login_failed", "failed", "bruteforce")
            flash("Invalid credentials", "danger")
            return render_template("auth/login.html")

        now = datetime.utcnow()

        # ---------------- LOCK CHECK ----------------
        if hasattr(user, "lockout_until") and user.lockout_until:
            if user.lockout_until > now:
                write_log(username, "login_blocked", "locked", "bruteforce")
                flash("Account locked. Try later.", "danger")
                return render_template("auth/login.html")

        # ---------------- PASSWORD CHECK ----------------
        if not user.check_password(password):

            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

            # BRUTE FORCE DETECTION
            if user.failed_login_attempts >= 5:
                user.lockout_until = now + timedelta(minutes=5)
                user.failed_login_attempts = 0

                write_log(
                    username,
                    "bruteforce_detected",
                    "blocked",
                    "bruteforce"
                )

            db.session.commit()

            write_log(username, "login_failed", "failed", "login")

            flash("Invalid credentials", "danger")
            return render_template("auth/login.html")

        # reset counters
        user.failed_login_attempts = 0
        user.lockout_until = None
        db.session.commit()

        write_log(username, "login_success", "success", "login")

        # ---------------- FIRST LOGIN ----------------
        if getattr(user, "first_login", False):
            session["change_pass_user"] = user.id
            session["change_pass_type"] = user_type
            return redirect(url_for("auth.change_password"))

        # ---------------- MFA ----------------
        if getattr(user, "mfa_enabled", False):

            session["pre_2fa_user"] = user.id
            session["pre_2fa_type"] = user_type

            if not user.totp_secret:
                return redirect(url_for("auth.enable_2fa"))

            return redirect(url_for("auth.twofa"))

        # ---------------- LOGIN ----------------
        login_user(user, remember=bool(request.form.get("remember")))
        flash("Logged in successfully", "success")
        return _redirect_for_user_type(user_type)

    return render_template("auth/login.html")



@auth_bp.route("/enable_2fa", methods=["GET", "POST"])
def enable_2fa():

    user_id = session.get("pre_2fa_user")
    user_type = session.get("pre_2fa_type")

    if not user_id:
        return redirect(url_for("auth.login"))

    user = AdminAccount.query.get(user_id) if user_type == "admin" else User.query.get(user_id)

    if not user:
        return redirect(url_for("auth.login"))

    if not user.totp_secret:
        user.generate_totp_secret()
        db.session.commit()

    if request.method == "POST":

        code = request.form.get("code")

        if user.verify_totp(code):

            user.mfa_enabled = True
            db.session.commit()

            flash("2FA enabled successfully", "success")
            return redirect(url_for("auth.twofa"))

        flash("Invalid code", "danger")

    return render_template("auth/enable_2fa.html", secret=user.totp_secret)



@auth_bp.route("/qrcode")
def qrcode_image():

    user_id = session.get("pre_2fa_user")
    user_type = session.get("pre_2fa_type")

    if not user_id:
        return "Session expired", 400

    user = AdminAccount.query.get(user_id) if user_type == "admin" else User.query.get(user_id)

    if not user or not user.totp_secret:
        return "No TOTP secret", 400

    uri = user.get_totp_uri()
    qr = qrcode.make(uri)

    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")



@auth_bp.route("/twofa", methods=["GET", "POST"])
def twofa():

    user_id = session.get("pre_2fa_user")
    user_type = session.get("pre_2fa_type")

    if not user_id:
        return redirect(url_for("auth.login"))

    user = AdminAccount.query.get(user_id) if user_type == "admin" else User.query.get(user_id)

    if request.method == "POST":

        code = request.form.get("code")

        if user.verify_totp(code):

            login_user(user)

            session.pop("pre_2fa_user", None)
            session.pop("pre_2fa_type", None)

            flash("2FA successful", "success")
            return _redirect_for_user_type(user_type)

        flash("Invalid 2FA code", "danger")
        write_log(get_email(user), "2fa_failed", "failed", "mfa")

    return render_template("auth/twofa.html")


@auth_bp.route("/change_password", methods=["GET", "POST"])
def change_password():

    user_id = session.get("change_pass_user")
    user_type = session.get("change_pass_type")

    if not user_id:
        return redirect(url_for("auth.login"))

    user = AdminAccount.query.get(user_id) if user_type == "admin" else User.query.get(user_id)
    if not user:
        session.clear()
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    require_security_setup = isinstance(user, User) and not user.has_security_question

    if request.method == "POST":

        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("auth.change_password"))

        if require_security_setup:
            question_key = request.form.get("security_question", "").strip()
            security_answer = request.form.get("security_answer", "")
            confirm_security_answer = request.form.get("confirm_security_answer", "")

            if question_key not in SECURITY_QUESTION_MAP:
                flash("Please select a valid security question.", "danger")
                return redirect(url_for("auth.change_password"))

            if security_answer != confirm_security_answer:
                flash("Security answers do not match.", "danger")
                return redirect(url_for("auth.change_password"))

            try:
                user.set_security_question(question_key, security_answer)
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("auth.change_password"))

        user.set_password(new_password)
        if hasattr(user, "first_login"):
            user.first_login = False
        db.session.commit()

        session.clear()

        flash("Password updated", "success")
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/change_password.html",
        require_security_setup=require_security_setup,
        security_questions=SECURITY_QUESTION_CHOICES,
    )


@auth_bp.route("/security-question/setup", methods=["GET", "POST"])
@login_required
def setup_security_question():
    if current_user.__class__.__name__ == "AdminAccount":
        flash("Security question setup is available for user accounts only.", "warning")
        return redirect(url_for("admin.admin_dashboard"))

    user = User.query.get(current_user.id)
    if user is None:
        flash("Unable to load account.", "danger")
        return redirect(url_for("auth.logout"))

    if request.method == "POST":
        question_key = request.form.get("security_question", "").strip()
        security_answer = request.form.get("security_answer", "")
        confirm_security_answer = request.form.get("confirm_security_answer", "")

        if question_key not in SECURITY_QUESTION_MAP:
            flash("Please select a valid security question.", "danger")
            return redirect(url_for("auth.setup_security_question"))

        if security_answer != confirm_security_answer:
            flash("Security answers do not match.", "danger")
            return redirect(url_for("auth.setup_security_question"))

        try:
            user.set_security_question(question_key, security_answer)
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("auth.setup_security_question"))

        db.session.commit()
        flash("Security question saved successfully.", "success")
        return _redirect_for_user_type(user.user_type)

    return render_template(
        "auth/security_question_setup.html",
        security_questions=SECURITY_QUESTION_CHOICES,
        current_question=user.security_question,
        current_question_label=_security_question_label(user.security_question),
    )


@auth_bp.route("/logout")
@login_required
def logout():

    write_log(get_email(current_user), "logout", "success", "session")

    logout_user()
    session.clear()

    flash("Logged out", "success")
    return redirect(url_for("main.index"))



@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        user = (
            User.query.filter(db.func.lower(User.personal_email) == email).first()
            if email
            else None
        )

        if user:
            token = user.get_reset_token()
            link = url_for("auth.reset_password", token=token, _external=True)

            msg = Message(
                "Reset Password",
                sender=current_app.config.get("MAIL_USERNAME", "no-reply@localhost"),
                recipients=[email],
            )

            msg.body = (
                "You requested a password reset for your IAM account.\n\n"
                f"Use this link to reset your password:\n{link}\n\n"
                "If you did not request this reset, you can ignore this email."
            )
            try:
                mail.send(msg)
            except Exception:
                current_app.logger.exception("Password reset email delivery failed")

        flash(
            "If an account exists for that email, a password reset link has been sent.",
            "info",
        )
        return redirect(url_for("auth.forgot_password"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/recover/security-question", methods=["GET", "POST"])
def recover_with_security_question():
    user, session_error = _load_security_recovery_user()
    recovery_config = _get_security_recovery_config()

    if session_error == "expired":
        flash("Recovery session expired. Please start again.", "warning")

    if request.method == "POST":
        if user is None:
            email = request.form.get("email", "").strip().lower()
            candidate = (
                User.query.filter(db.func.lower(User.personal_email) == email).first()
                if email
                else None
            )

            if (
                candidate is not None
                and candidate.has_security_question
                and not candidate.is_security_recovery_locked()
            ):
                _start_security_recovery_session(candidate.id)
                flash("Answer your security question to continue.", "info")
                return redirect(url_for("auth.recover_with_security_question"))

            flash(
                "If that account is eligible, continue with email reset or contact support.",
                "info",
            )
            return redirect(url_for("auth.recover_with_security_question"))

        answer = request.form.get("security_answer", "")

        if user.is_security_recovery_locked():
            _clear_security_recovery_session()
            flash(
                "Security-question recovery is temporarily locked. Use email reset or try later.",
                "danger",
            )
            return redirect(url_for("auth.recover_with_security_question"))

        if user.verify_security_answer(answer):
            user.clear_security_recovery_failures()
            db.session.commit()
            _clear_security_recovery_session()

            token = user.get_reset_token()
            flash("Identity verified. Set your new password.", "success")
            return redirect(url_for("auth.reset_password", token=token))

        locked = user.register_security_recovery_failure(
            max_attempts=recovery_config["max_attempts"],
            lock_minutes=recovery_config["lockout_minutes"],
        )
        db.session.commit()

        if locked:
            _clear_security_recovery_session()
            flash(
                "Too many incorrect answers. Security-question recovery is locked temporarily.",
                "danger",
            )
            return redirect(url_for("auth.recover_with_security_question"))

        remaining_attempts = max(
            0,
            recovery_config["max_attempts"] - int(user.security_failed_attempts or 0),
        )
        flash(
            f"Incorrect answer. {remaining_attempts} attempt(s) remaining.",
            "danger",
        )
        return redirect(url_for("auth.recover_with_security_question"))

    return render_template(
        "auth/security_question_recovery.html",
        challenge_active=user is not None,
        question_label=_security_question_label(user.security_question) if user else None,
        masked_email=_mask_email(user.personal_email) if user else None,
    )


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):

    expires_seconds = int(current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRES_SECONDS", 1800))
    user = User.verify_reset_token(token, expires_sec=expires_seconds)

    if not user:
        flash("Invalid token", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":

        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(request.url)

        user.set_password(new_password)
        _clear_security_recovery_session()
        db.session.commit()

        flash("Password reset success", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html")

from functools import wraps

from flask import jsonify, redirect, request, session, url_for
from flask_login import current_user

from app import db
from app.models import Permission, Role


DEFAULT_PERMISSIONS = {
    "identity.read": "View identities",
    "identity.write": "Create or update identities",
    "admin.dashboard": "Access admin dashboard",
    "admin.audit": "View security audit",
    "admin.manage_mfa": "Manage user MFA",
}

DEFAULT_ROLES = {
    "super_admin": {
        "description": "Full IAM administration",
        "required_auth_level": 1,
        "permissions": list(DEFAULT_PERMISSIONS.keys()),
    },
    "auditor": {
        "description": "Read-only security auditing",
        "required_auth_level": 1,
        "permissions": ["admin.audit", "identity.read"],
    },
    "identity_manager": {
        "description": "Identity lifecycle management",
        "required_auth_level": 1,
        "permissions": ["identity.read", "identity.write", "admin.dashboard"],
    },
    "basic_user": {
        "description": "Standard user",
        "required_auth_level": 1,
        "permissions": [],
    },
}


def ensure_authorization_seed_data():
    """Create baseline roles/permissions when missing."""
    permissions_by_name = {}
    changed = False

    for name, description in DEFAULT_PERMISSIONS.items():
        permission = Permission.query.filter_by(name=name).first()
        if permission is None:
            permission = Permission(name=name, description=description)
            db.session.add(permission)
            changed = True
        permissions_by_name[name] = permission

    db.session.flush()

    for role_name, payload in DEFAULT_ROLES.items():
        role = Role.query.filter_by(name=role_name).first()
        if role is None:
            role = Role(
                name=role_name,
                description=payload["description"],
                required_auth_level=payload["required_auth_level"],
            )
            db.session.add(role)
            db.session.flush()
            changed = True

        desired = set(payload["permissions"])
        current = {p.name for p in role.permissions}
        if desired != current:
            role.permissions = [permissions_by_name[name] for name in sorted(desired)]
            changed = True

    if changed:
        db.session.commit()


def _effective_auth_level():
    return int(session.get("auth_level", getattr(current_user, "session_auth_level", 1) or 1))


def _role_names_for_current_user():
    if not current_user.is_authenticated:
        return set()

    if current_user.__class__.__name__ == "AdminAccount":
        role_names = {role.name for role in getattr(current_user, "roles", [])}
        return role_names or {"super_admin"}

    role_name = getattr(current_user, "role_name", None)
    return {role_name} if role_name else {"basic_user"}


def current_user_has_permission(permission_name):
    role_names = _role_names_for_current_user()
    if not role_names:
        return False

    roles = Role.query.filter(Role.name.in_(list(role_names))).all()
    available = {p.name for role in roles for p in role.permissions}
    return permission_name in available


def admin_has_permission(admin, permission_name):
    role_names = {role.name for role in getattr(admin, "roles", [])} or {"super_admin"}
    roles = Role.query.filter(Role.name.in_(list(role_names))).all()
    available = {p.name for role in roles for p in role.permissions}
    return permission_name in available


def admin_required_auth_level(admin):
    roles = list(getattr(admin, "roles", []) or [])
    if not roles:
        return int(getattr(admin, "required_auth_level", 2) or 2)
    return max(int(getattr(admin, "required_auth_level", 2) or 2), max(int(r.required_auth_level or 1) for r in roles))


def require_permission(permission_name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not current_user_has_permission(permission_name):
                if request.path.startswith("/api"):
                    return jsonify({"error": "permission denied"}), 403
                return redirect(url_for("main.index"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_auth_level(level):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if _effective_auth_level() < int(level):
                if request.path.startswith("/api"):
                    return jsonify({"error": f"auth level L{level} required"}), 403
                return redirect(url_for("auth.login"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator

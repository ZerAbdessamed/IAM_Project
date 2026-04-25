from flask import render_template, request, redirect, url_for, flash, session, send_file
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
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []
    else:
        data = []

    data.append(log_entry)

    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)



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

        if user_type == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        elif user_type == "student":
            return redirect(url_for("main.student_profile"))
        else:
            return redirect(url_for("main.staff_profile"))

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

            if user_type == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            elif user_type == "student":
                return redirect(url_for("main.student_profile"))
            else:
                return redirect(url_for("main.staff_profile"))

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

    if request.method == "POST":

        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("auth.change_password"))

        user.set_password(new_password)
        user.first_login = False
        db.session.commit()

        session.clear()

        flash("Password updated", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/change_password.html")


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

        email = request.form.get("email")
        user = User.query.filter_by(personal_email=email).first()

        if user:
            token = user.get_reset_token()
            link = url_for("auth.reset_password", token=token, _external=True)

            msg = Message(
                "Reset Password",
                sender="your-email@gmail.com",
                recipients=[email]
            )

            msg.body = f"Reset link:\n{link}"
            mail.send(msg)

            flash("Email sent", "info")
        else:
            flash("Email not found", "danger")

    return render_template("auth/forgot_password.html")



@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):

    user = User.verify_reset_token(token)

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
        db.session.commit()

        flash("Password reset success", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html")
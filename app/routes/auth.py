# app/routes/auth.py

from flask import render_template, request, redirect, url_for, flash, session, send_file
from flask_login import login_user, logout_user, login_required, current_user
from app.models import AdminAccount
from app.models.user import User
from app.routes import auth_bp
from app import db, mail
from flask_mail import Message
import qrcode
import io


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user_type = request.form.get('user_type')

        user = None
        if user_type == "admin":
            user = AdminAccount.query.filter(
                (AdminAccount.username == username_or_email) |
                (AdminAccount.email == username_or_email)
            ).first()
        elif user_type in ["student", "staff"]:
            user = User.query.filter(
                (User.personal_email == username_or_email) &
                (User.user_type == user_type)
            ).first()

        if user is None or not user.check_password(password):
            flash('Invalid credentials.', 'danger')
            return render_template('auth/login.html')

        if hasattr(user, 'first_login') and user.first_login:
            session['change_pass_user'] = user.id
            session['change_pass_type'] = user_type
            flash("You must change your password on first login.", "warning")
            return redirect(url_for('auth.change_password'))

        admin = AdminAccount.query.first()
        admin_mfa_active = getattr(admin, 'manage_mfa_enabled', False)

        if admin_mfa_active and not user.totp_secret:
            user.generate_totp_secret()
            db.session.commit()
            login_user(user)
            flash("Admin has enabled 2FA. Please set up your 2FA first.", "info")
            return redirect(url_for("auth.enable_2fa"))

        if (admin_mfa_active or getattr(user, 'mfa_enabled', False)) and user.totp_secret:
            session['pre_2fa_user'] = user.id
            session['pre_2fa_type'] = user_type
            return redirect(url_for('auth.twofa'))

        login_user(user, remember=bool(request.form.get('remember')))
        flash('Logged in successfully.', 'success')

        if user_type == "admin":
            return redirect(url_for('admin.admin_dashboard'))
        elif user_type == "student":
            return redirect(url_for('main.student_profile'))
        elif user_type == "staff":
            return redirect(url_for('main.staff_profile'))

    return render_template('auth/login.html')



@auth_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    user_id = session.get('change_pass_user')
    user_type = session.get('change_pass_type')

    if not user_id:
        return redirect(url_for('auth.login'))

    if user_type == "admin":
        user = AdminAccount.query.get(user_id)
    else:
        user = User.query.get(user_id)

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for('auth.change_password'))

        user.set_password(new_password)
        user.first_login = False
        db.session.commit()

        session.pop('change_pass_user')
        session.pop('change_pass_type')

        flash("Password changed successfully. Please login again.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/change_password.html')



@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('main.index'))



@auth_bp.route("/qrcode")
@login_required
def qrcode_image():
    if not current_user.totp_secret:
        return "No TOTP secret found", 400

    uri = current_user.get_totp_uri()
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@auth_bp.route('/twofa', methods=['GET', 'POST'])
def twofa():
    user_id = session.get('pre_2fa_user')
    user_type = session.get('pre_2fa_type')

    if not user_id:
        return redirect(url_for('auth.login'))

    if user_type == "admin":
        user = AdminAccount.query.get(user_id)
    else:
        user = User.query.get(user_id)

    if request.method == "POST":
        code = request.form.get('code')
        if hasattr(user, 'verify_totp') and user.verify_totp(code):
            login_user(user)
            session.pop('pre_2fa_user')
            session.pop('pre_2fa_type')
            flash('2FA verification successful!', 'success')

            if user_type == "admin":
                return redirect(url_for('admin.admin_dashboard'))
            elif user_type == "student":
                return redirect(url_for('main.student_profile'))
            elif user_type == "staff":
                return redirect(url_for('main.staff_profile'))
        else:
            flash('Invalid 2FA code.', 'danger')

    return render_template('auth/twofa.html')


@auth_bp.route("/enable_2fa", methods=["GET", "POST"])
@login_required
def enable_2fa():
    user = current_user
    admin = AdminAccount.query.first()
    admin_mfa_active = getattr(admin, 'manage_mfa_enabled', False)

    if not admin_mfa_active:
        flash("2FA is not enabled for your account. Contact admin.", "warning")
        return redirect(url_for('main.index'))

    if request.method == "POST":
        code = request.form.get("code")
        if user.verify_totp(code):
            user.mfa_enabled = True
            db.session.commit()
            flash("2FA enabled successfully!", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Invalid code. Try again.", "danger")

    if not user.totp_secret:
        user.generate_totp_secret()
        db.session.commit()

    qr_uri = user.get_totp_uri()
    return render_template("auth/enable_2fa.html", qr_uri=qr_uri, secret=user.totp_secret)



@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(personal_email=email).first()

        if user:
            token = user.get_reset_token()
            reset_link = url_for('auth.reset_password', token=token, _external=True)

            msg = Message(subject="IAM Password Reset",
                          sender="your-email@gmail.com",
                          recipients=[email])
            msg.body = f"Hello {user.first_name},\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you didn't request this, ignore this email."
            mail.send(msg)

            flash("Password reset link has been sent to your email.", "info")
        else:
            flash("Email not found.", "danger")

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash("The reset link is invalid or has expired.", "danger")
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for('auth.reset_password', token=token))

        user.set_password(new_password)
        db.session.commit()

        flash("Password has been reset successfully. Please login.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
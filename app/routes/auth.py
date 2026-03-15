from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from app.models import AdminAccount
from app.models.user import User
from app.routes import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user_type = request.form.get('user_type')

        if user_type == "admin":
            admin = AdminAccount.query.filter(
                (AdminAccount.username == username_or_email) |
                (AdminAccount.email == username_or_email)
            ).first()
            if admin is None or not admin.check_password(password):
                flash('Invalid credentials.', 'danger')
                return render_template('auth/login.html')
            if not admin.is_active:
                flash('Account is inactive.', 'danger')
                return render_template('auth/login.html')
            login_user(admin, remember=bool(request.form.get('remember')))
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin.admin_dashboard'))

        elif user_type == "student":
            u = User.query.filter(
                (User.personal_email == username_or_email) &
                (User.user_type == "student")
            ).first()
            if u is None or not u.check_password(password):
                flash('Invalid credentials.', 'danger')
                return render_template('auth/login.html')
            login_user(u, remember=bool(request.form.get('remember')))
            flash('Logged in successfully.', 'success')
            return redirect(url_for('main.student_profile'))

        elif user_type == "staff":
            s = User.query.filter(
                (User.personal_email == username_or_email) &
                (User.user_type == "staff")
            ).first()
            if s is None or not s.check_password(password):
                flash('Invalid credentials.', 'danger')
                return render_template('auth/login.html')
            login_user(s, remember=bool(request.form.get('remember')))
            flash('Logged in successfully.', 'success')
            return redirect(url_for('main.staff_profile'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Logout user."""
    logout_user()
    return redirect(url_for('main.index'))

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.routes import admin_bp
from app.models.user import User
from app.models.admin_account import AdminAccount
from app import db


@admin_bp.route('/')
@login_required
def admin_dashboard():
    """Admin dashboard."""
    if current_user.__class__.__name__ != 'AdminAccount':
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    admin = AdminAccount.query.get(current_user.id)
    return render_template('admin/dashboard.html', admin=admin)



@admin_bp.route('/manage_2fa', methods=['GET', 'POST'])
@login_required
def manage_2fa():
    """Allow admin to enable or disable 2FA for any user."""
    if current_user.__class__.__name__ != 'AdminAccount':
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    users = User.query.all()

    if request.method == "POST":
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        user = User.query.get(user_id)

        if user:
            if action == "enable":
                user.mfa_enabled = True
                flash(f"2FA enabled for {user.first_name} {user.last_name}", "success")
            elif action == "disable":
                user.mfa_enabled = False
                flash(f"2FA disabled for {user.first_name} {user.last_name}", "warning")
            db.session.commit()
        return redirect(url_for('admin.manage_2fa'))

    return render_template('admin/manage_2fa.html', users=users)
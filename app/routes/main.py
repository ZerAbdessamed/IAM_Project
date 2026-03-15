from flask import render_template
from flask_login import login_required, current_user
from app.routes import main_bp
from app.models.user import User

@main_bp.route('/')
def index():
    """Home page."""
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard"""
    counts = {
        'students': User.query.filter_by(user_type='student').count(),
        'faculty': User.query.filter_by(user_type='faculty').count(),
        'staff': User.query.filter_by(user_type='staff').count(),
        'total': User.query.count(),
    }
    return render_template('dashboard.html', counts=counts)


@main_bp.route('/student/profile')
@login_required
def student_profile():
    """Student profile view."""
    return render_template('student/student_view.html', student=current_user)


@main_bp.route('/staff/profile')
@login_required
def staff_profile():
    """Staff profile view."""
    return render_template('staff/staff_view.html', staff=current_user)

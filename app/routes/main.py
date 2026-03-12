from flask import render_template
from app.routes import main_bp
from app.models import User


@main_bp.route('/')
def index():
    """Home page."""
    return render_template('index.html')


@main_bp.route('/dashboard')
def dashboard():
    """Dashboard page."""
    counts = {
        'students': User.query.filter_by(user_type='student').count(),
        'faculty': User.query.filter_by(user_type='faculty').count(),
        'staff': User.query.filter_by(user_type='staff').count(),
        'total': User.query.count(),
    }
    return render_template('dashboard.html', counts=counts)

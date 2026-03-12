# Admin routes
from flask import render_template
from app.routes import admin_bp


@admin_bp.route('/')
def admin_dashboard():
    """Admin dashboard."""
    return render_template('admin/dashboard.html')

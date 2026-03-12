from flask import abort, flash, redirect, render_template, request, url_for

from app.models import IdentityChangeLog, User
from app.routes import identity_bp
from app.services.identity_service import (
    IdentityValidationError,
    create_identity,
    search_identities,
    transition_identity_status,
    update_identity,
)


IDENTITY_STATUSES = ['pending', 'active', 'suspended', 'inactive', 'archived']
USER_TYPES = ['student', 'faculty', 'staff', 'external']


@identity_bp.route('/')
def list_identities():
    """List and search identities with filtering options."""
    q = request.args.get('q', '').strip()
    user_type = request.args.get('type', '').strip().lower()
    status = request.args.get('status', '').strip().lower()
    year = request.args.get('year', '').strip()

    identities = search_identities(
        search_text=q or None,
        user_type=user_type or None,
        status=status or None,
        year=year or None,
    )

    return render_template(
        'identity/list.html',
        identities=identities,
        filters={'q': q, 'type': user_type, 'status': status, 'year': year},
    )


@identity_bp.route('/create', methods=['GET', 'POST'])
def create_identity_view():
    """Create a new identity with common and category-specific fields."""
    if request.method == 'POST':
        try:
            user = create_identity(request.form)
            flash(f'Identity {user.unique_identifier} created successfully.', 'success')
            return redirect(url_for('identity.view_identity', user_id=user.id))
        except IdentityValidationError as exc:
            flash(str(exc), 'danger')

    return render_template(
        'identity/form.html',
        mode='create',
        user=None,
        statuses=IDENTITY_STATUSES,
        user_types=USER_TYPES,
    )


@identity_bp.route('/<int:user_id>')
def view_identity(user_id):
    """Show details for one identity."""
    user = User.query.get_or_404(user_id)
    changes = (
        IdentityChangeLog.query.filter_by(user_id=user.id)
        .order_by(IdentityChangeLog.changed_at.desc())
        .limit(20)
        .all()
    )
    return render_template('identity/detail.html', user=user, changes=changes)


@identity_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_identity(user_id):
    """Edit identity details and keep change history."""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        try:
            update_identity(user, request.form)
            flash('Identity updated successfully.', 'success')
            return redirect(url_for('identity.view_identity', user_id=user.id))
        except IdentityValidationError as exc:
            flash(str(exc), 'danger')

    return render_template(
        'identity/form.html',
        mode='edit',
        user=user,
        statuses=IDENTITY_STATUSES,
        user_types=USER_TYPES,
    )


@identity_bp.route('/<int:user_id>/status', methods=['POST'])
def change_status(user_id):
    """Change identity lifecycle status using allowed transitions."""
    user = User.query.get_or_404(user_id)
    new_status = request.form.get('status', '').strip().lower()

    if new_status not in IDENTITY_STATUSES:
        abort(400, 'Invalid status value')

    try:
        transition_identity_status(user, new_status)
        flash(f'Status changed to {new_status}.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')

    return redirect(url_for('identity.view_identity', user_id=user.id))


@identity_bp.route('/<int:user_id>/deactivate', methods=['POST'])
def deactivate_identity(user_id):
    """Shortcut action for Active -> Inactive transition."""
    user = User.query.get_or_404(user_id)
    try:
        transition_identity_status(user, 'inactive')
        flash('Identity deactivated (inactive).', 'warning')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('identity.list_identities'))

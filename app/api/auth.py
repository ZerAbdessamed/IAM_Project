from flask import jsonify, request
from sqlalchemy import or_

from app.api import api_auth_bp
from app import db
from app.models import AdminAccount


def _serialize_admin(admin):
    return {
        'id': admin.id,
        'username': admin.username,
        'email': admin.email,
        'full_name': admin.full_name,
        'created_at': admin.created_at.isoformat() if admin.created_at else None,
    }


@api_auth_bp.route('/admin/register', methods=['POST'])
def register_admin():
    """
    Register an admin account
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/AdminRegisterRequest'
    responses:
      201:
        description: Admin account created
        schema:
          $ref: '#/definitions/AdminAuthResponse'
      400:
        description: Validation error
        schema:
          $ref: '#/definitions/ErrorResponse'
      403:
        description: Invalid bootstrap key
        schema:
          $ref: '#/definitions/ErrorResponse'
    """
    payload = request.get_json(silent=True) or {}

    username = str(payload.get('username', '')).strip().lower()
    email = str(payload.get('email', '')).strip().lower()
    full_name = str(payload.get('full_name', '')).strip()
    password = str(payload.get('password', ''))

    if not username or not email or not full_name or not password:
        return jsonify({'error': 'username, email, full_name and password are required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'password must be at least 8 characters'}), 400

    # Optional: enforce bootstrap key through env var when configured.
    from os import getenv

    configured_bootstrap_key = getenv('ADMIN_BOOTSTRAP_KEY', '').strip()
    provided_bootstrap_key = str(payload.get('bootstrap_key', '')).strip()
    if configured_bootstrap_key and configured_bootstrap_key != provided_bootstrap_key:
        return jsonify({'error': 'invalid bootstrap_key'}), 403

    duplicate = AdminAccount.query.filter(
        or_(AdminAccount.username == username, AdminAccount.email == email)
    ).first()
    if duplicate is not None:
        return jsonify({'error': 'admin with same username or email already exists'}), 400

    admin = AdminAccount(username=username, email=email, full_name=full_name)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    return jsonify({'message': 'admin registered successfully', 'admin': _serialize_admin(admin)}), 201


@api_auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate admin
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - username_or_email
            - password
          properties:
            username_or_email:
              type: string
              example: admin
            password:
              type: string
              format: password
              example: SecurePass123!
    responses:
      200:
        description: Login successful
        schema:
          $ref: '#/definitions/AdminAuthResponse'
      401:
        description: Invalid credentials
        schema:
          $ref: '#/definitions/ErrorResponse'
    """
    payload = request.get_json(silent=True) or {}
    username_or_email = str(payload.get('username_or_email', '')).strip().lower()
    password = str(payload.get('password', ''))

    if not username_or_email or not password:
        return jsonify({'error': 'username_or_email and password are required'}), 400

    admin = AdminAccount.query.filter(
        or_(AdminAccount.username == username_or_email, AdminAccount.email == username_or_email)
    ).first()

    if admin is None or not admin.check_password(password):
        return jsonify({'error': 'invalid credentials'}), 401

    if not admin.is_active:
        return jsonify({'error': 'account is inactive'}), 403

    return jsonify({'message': 'login successful', 'admin': _serialize_admin(admin)})


@api_auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    End session
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Logged out successfully
    """
    return jsonify({'message': 'Logged out'})


@api_auth_bp.route('/session', methods=['GET'])
def session_info():
    """
    Get current session info
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Session information
        schema:
          type: object
          properties:
            session:
              type: object
              properties:
                user_id:
                  type: integer
                auth_level:
                  type: string
                expires_at:
                  type: string
                  format: datetime
    """
    return jsonify({'session': None})


@api_auth_bp.route('/password/change', methods=['POST'])
def change_password():
    """
    Change password
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - current_password
            - new_password
            - confirm_password
          properties:
            current_password:
              type: string
              format: password
            new_password:
              type: string
              format: password
              description: "Min 8 chars, must contain 3 of: uppercase, lowercase, numbers, special chars"
            confirm_password:
              type: string
              format: password
    responses:
      200:
        description: Password changed successfully
      400:
        description: Password does not meet requirements
      401:
        description: Current password incorrect
    """
    return jsonify({'message': 'Password change API'})


@api_auth_bp.route('/password/reset', methods=['POST'])
def reset_password():
    """
    Request password reset
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              example: john.doe@university.edu
    responses:
      200:
        description: Password reset email sent
      404:
        description: Email not found
    """
    return jsonify({'message': 'Password reset API'})

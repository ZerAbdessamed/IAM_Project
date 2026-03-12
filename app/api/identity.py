from flask import jsonify, request

from app.api import api_identity_bp
from app.models import User
from app.services.identity_service import (
  IdentityValidationError,
  create_identity as create_identity_service,
  search_identities as search_identities_service,
  transition_identity_status,
  update_identity as update_identity_service,
)


def _to_iso(value):
  return value.isoformat() if value is not None else None


def _serialize_identity(user):
  payload = {
    'id': user.id,
    'unique_identifier': user.unique_identifier,
    'first_name': user.first_name,
    'last_name': user.last_name,
    'date_of_birth': _to_iso(user.date_of_birth),
    'place_of_birth': user.place_of_birth,
    'nationality': user.nationality,
    'gender': user.gender,
    'personal_email': user.personal_email,
    'phone_number': user.phone_number,
    'user_type': user.user_type,
    'identity_status': user.identity_status,
    'created_at': _to_iso(user.created_at),
    'updated_at': _to_iso(user.updated_at),
    'profile': {},
  }

  if user.user_type == 'student' and user.student_profile is not None:
    p = user.student_profile
    payload['profile'] = {
      'student_category': p.student_category,
      'national_id_number': p.national_id_number,
      'high_school_diploma_type': p.high_school_diploma_type,
      'high_school_diploma_year': p.high_school_diploma_year,
      'high_school_honors': p.high_school_honors,
      'major_program': p.major_program,
      'entry_year': p.entry_year,
      'academic_status': p.academic_status,
      'faculty': p.faculty,
      'department': p.department,
      'group_name': p.group_name,
      'scholarship_status': p.scholarship_status,
    }
  elif user.user_type == 'faculty' and user.faculty_profile is not None:
    p = user.faculty_profile
    payload['profile'] = {
      'faculty_category': p.faculty_category,
      'rank': p.rank,
      'employment_category': p.employment_category,
      'appointment_start_date': _to_iso(p.appointment_start_date),
      'primary_department': p.primary_department,
      'secondary_departments': p.secondary_departments,
      'office_building': p.office_building,
      'office_floor': p.office_floor,
      'office_room_number': p.office_room_number,
      'phd_institution': p.phd_institution,
      'research_areas': p.research_areas,
      'habilitation_supervise_research': p.habilitation_supervise_research,
      'contract_type': p.contract_type,
      'contract_start_date': _to_iso(p.contract_start_date),
      'contract_end_date': _to_iso(p.contract_end_date),
      'teaching_hours': p.teaching_hours,
    }
  elif user.user_type == 'staff' and user.staff_profile is not None:
    p = user.staff_profile
    payload['profile'] = {
      'staff_category': p.staff_category,
      'assigned_department_service': p.assigned_department_service,
      'job_title': p.job_title,
      'grade': p.grade,
      'date_of_entry_university': _to_iso(p.date_of_entry_university),
      'contract_start_date': _to_iso(p.contract_start_date),
      'contract_end_date': _to_iso(p.contract_end_date),
    }
  elif user.user_type == 'external' and user.external_profile is not None:
    p = user.external_profile
    payload['profile'] = {
      'external_category': p.external_category,
      'organization': p.organization,
      'access_notes': p.access_notes,
      'access_start_date': _to_iso(p.access_start_date),
      'access_end_date': _to_iso(p.access_end_date),
      'alumni_class_year': p.alumni_class_year,
    }

  return payload


@api_identity_bp.route('/examples', methods=['GET'])
def identity_payload_examples():
  """
  Get sample payloads for each identity type
  ---
  tags:
    - Identity
  responses:
    200:
    description: Sample payloads for Swagger/Postman testing
    schema:
      $ref: '#/definitions/IdentityExamplesResponse'
  """
  return jsonify(
    {
      'student': {
        'user_type': 'student',
        'first_name': 'Lina',
        'last_name': 'Bouzid',
        'date_of_birth': '2004-05-14',
        'place_of_birth': 'Batna',
        'nationality': 'Algerian',
        'gender': 'F',
        'personal_email': 'lina.bouzid@example.com',
        'phone_number': '0550123456',
        'student_category': 'undergraduate',
        'national_id_number': 'STU-NID-001',
        'high_school_diploma_type': 'Scientific',
        'high_school_diploma_year': 2022,
        'high_school_honors': 'Excellent',
        'major_program': 'Computer Science',
        'entry_year': 2023,
        'academic_status': 'active',
        'faculty': 'Science Faculty',
        'department': 'Computer Science',
        'group_name': 'G1',
        'scholarship_status': True,
      },
      'faculty': {
        'user_type': 'faculty',
        'first_name': 'Oussama',
        'last_name': 'Harkati',
        'date_of_birth': '1985-11-20',
        'place_of_birth': 'Batna',
        'nationality': 'Algerian',
        'gender': 'M',
        'personal_email': 'oussama.harkati@example.com',
        'phone_number': '0660987654',
        'faculty_category': 'tenured',
        'rank': 'Associate Professor',
        'employment_category': 'Permanent',
        'appointment_start_date': '2015-09-01',
        'primary_department': 'Computer Science',
        'secondary_departments': 'Mathematics',
        'office_building': 'A',
        'office_floor': '2',
        'office_room_number': '214',
        'phd_institution': 'University of Batna 2',
        'research_areas': 'IAM, Security',
        'habilitation_supervise_research': True,
        'contract_type': 'Permanent',
        'contract_start_date': '2015-09-01',
        'contract_end_date': None,
        'teaching_hours': 180,
      },
      'staff': {
        'user_type': 'staff',
        'first_name': 'Amine',
        'last_name': 'Khelifi',
        'date_of_birth': '1990-03-08',
        'place_of_birth': 'Setif',
        'nationality': 'Algerian',
        'gender': 'M',
        'personal_email': 'amine.khelifi@example.com',
        'phone_number': '0770112233',
        'staff_category': 'administrative',
        'assigned_department_service': 'Registrar Office',
        'job_title': 'Administrative Officer',
        'grade': 'A2',
        'date_of_entry_university': '2019-02-01',
        'contract_start_date': '2019-02-01',
        'contract_end_date': None,
      },
      'external': {
        'user_type': 'external',
        'first_name': 'Nadia',
        'last_name': 'Saidi',
        'date_of_birth': '1988-01-17',
        'place_of_birth': 'Algiers',
        'nationality': 'Algerian',
        'gender': 'F',
        'personal_email': 'nadia.saidi@example.com',
        'phone_number': '0555001122',
        'external_category': 'contractor_vendor',
        'organization': 'TechVendor Ltd',
        'access_notes': 'Temporary lab network maintenance access',
        'access_start_date': '2026-03-01',
        'access_end_date': '2026-06-01',
        'alumni_class_year': None,
      },
    }
  )


@api_identity_bp.route('/', methods=['GET'])
def list_identities():
    """
    List all identities
    ---
    tags:
      - Identity
    responses:
      200:
        description: List of identities
        schema:
          $ref: '#/definitions/IdentityListResponse'
    """
    identities = User.query.order_by(User.created_at.desc()).all()
    return jsonify({'identities': [_serialize_identity(u) for u in identities]})


@api_identity_bp.route('/<int:id>', methods=['GET'])
def get_identity(id):
    """
    Get identity by ID
    ---
    tags:
      - Identity
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: Identity ID
    responses:
      200:
        description: Identity details
        schema:
          $ref: '#/definitions/IdentityResponse'
      404:
        description: Identity not found
        schema:
          $ref: '#/definitions/ErrorResponse'
    """
    user = User.query.get(id)
    if user is None:
        return jsonify({'error': 'Identity not found'}), 404
    return jsonify({'identity': _serialize_identity(user)})


@api_identity_bp.route('/', methods=['POST'])
def create_identity():
    """
    Create new identity
    ---
    tags:
      - Identity
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/IdentityCreateRequest'
    responses:
      201:
        description: Identity created successfully
        schema:
          $ref: '#/definitions/IdentityResponse'
      400:
        description: Validation error
        schema:
          $ref: '#/definitions/ErrorResponse'
    """
    data = request.get_json(silent=True) or {}
    try:
        user = create_identity_service(data)
    except IdentityValidationError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify({'identity': _serialize_identity(user)}), 201


@api_identity_bp.route('/<int:id>', methods=['PUT'])
def update_identity(id):
    """
    Update identity
    ---
    tags:
      - Identity
    parameters:
      - name: id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/IdentityCreateRequest'
    responses:
      200:
        description: Identity updated
        schema:
          $ref: '#/definitions/IdentityResponse'
      404:
        description: Identity not found
        schema:
          $ref: '#/definitions/ErrorResponse'
      400:
        description: Validation error
        schema:
          $ref: '#/definitions/ErrorResponse'
    """
    user = User.query.get(id)
    if user is None:
        return jsonify({'error': 'Identity not found'}), 404

    data = request.get_json(silent=True) or {}
    try:
        updated = update_identity_service(user, data)
    except IdentityValidationError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify({'identity': _serialize_identity(updated)})


@api_identity_bp.route('/<int:id>', methods=['DELETE'])
def delete_identity(id):
    """
    Deactivate identity
    ---
    tags:
      - Identity
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Identity deactivated
        schema:
          $ref: '#/definitions/MessageResponse'
      404:
        description: Identity not found
        schema:
          $ref: '#/definitions/ErrorResponse'
    """
    user = User.query.get(id)
    if user is None:
        return jsonify({'error': 'Identity not found'}), 404

    if user.identity_status == 'inactive':
        return jsonify({'message': f'Identity {id} is already inactive'})

    try:
        transition_identity_status(user, 'inactive')
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify({'message': f'Identity {id} deactivated'})


@api_identity_bp.route('/search', methods=['GET'])
def search_identities():
    """
    Search identities
    ---
    tags:
      - Identity
    parameters:
      - name: q
        in: query
        type: string
        description: Search query (name, email, ID)
      - name: type
        in: query
        type: string
        enum: [student, faculty, staff, external]
        description: Filter by user type
      - name: status
        in: query
        type: string
        enum: [pending, active, suspended, inactive, archived]
        description: Filter by status
      - name: year
        in: query
        type: integer
        description: Filter by created year
    responses:
      200:
        description: Search results
        schema:
          $ref: '#/definitions/IdentityListResponse'
    """
    q = request.args.get('q', '').strip() or None
    user_type = request.args.get('type', '').strip().lower() or None
    status = request.args.get('status', '').strip().lower() or None
    year = request.args.get('year', '').strip() or None

    identities = search_identities_service(
        search_text=q,
        user_type=user_type,
        status=status,
        year=year,
    )
    return jsonify({'identities': [_serialize_identity(u) for u in identities]})

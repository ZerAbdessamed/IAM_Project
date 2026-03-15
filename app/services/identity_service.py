from datetime import date, datetime
import re

from app import db
from app.models import External, Faculty, IdentityChangeLog, Staff, Student, User
from werkzeug.security import generate_password_hash

class IdentityValidationError(ValueError):
    pass

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def evaluate_password_strength(password: str) -> str:
    """Return password strength: Weak, Medium, Strong"""
    score = 0

    if len(password) >= 8:
        score += 1
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1

    if score <= 1:
        return "Weak"
    elif score <= 3:
        return "Medium"
    else:
        return "Strong"


def _parse_date(value, field_name):
    if isinstance(value, date):
        return value

    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise IdentityValidationError(f"{field_name} must be in YYYY-MM-DD format")


def _required(data, key, label):
    value = str(data.get(key, "")).strip()
    if not value:
        raise IdentityValidationError(f"{label} is required")
    return value


def _validate_common_payload(data, user_id=None):
    first_name = _required(data, "first_name", "First name")
    last_name = _required(data, "last_name", "Last name")

    if len(first_name) < 2 or len(last_name) < 2:
        raise IdentityValidationError("First name and last name must be at least 2 characters")

    dob = _parse_date(_required(data, "date_of_birth", "Date of birth"), "Date of birth")
    if dob > date.today():
        raise IdentityValidationError("Date of birth cannot be in the future")

    user_type = _required(data, "user_type", "User type").lower()
    if user_type not in {"student", "faculty", "staff", "external"}:
        raise IdentityValidationError("User type must be student, faculty, staff, or external")

    if user_type == "student":
        age = (date.today() - dob).days // 365
        if age < 16:
            raise IdentityValidationError("Minimum age is 16 for students")

    personal_email = _required(data, "personal_email", "Personal email").lower()
    if not EMAIL_REGEX.match(personal_email):
        raise IdentityValidationError("Personal email is invalid")

    duplicate_email = User.query.filter(User.personal_email == personal_email)
    if user_id is not None:
        duplicate_email = duplicate_email.filter(User.id != user_id)
    if duplicate_email.first() is not None:
        raise IdentityValidationError("Personal email must be unique")

    phone_number = _required(data, "phone_number", "Phone number")
    if not phone_number.isdigit():
        raise IdentityValidationError("Phone number must contain only numbers")

    first_name_norm = first_name.strip().lower()
    last_name_norm = last_name.strip().lower()
    duplicate_query = User.query.filter(
        db.func.lower(User.first_name) == first_name_norm,
        db.func.lower(User.last_name) == last_name_norm,
        User.date_of_birth == dob,
    )
    if user_id is not None:
        duplicate_query = duplicate_query.filter(User.id != user_id)
    if duplicate_query.first() is not None:
        raise IdentityValidationError("Duplicate identity detected (same name and date of birth)")

    # === PASSWORD VALIDATION ===
    password = _required(data, "password", "Password")
    password_confirm = _required(data, "conf_password", "Confirm Password")

    if password != password_confirm:
        raise IdentityValidationError("Password and confirm password must match")

    strength = evaluate_password_strength(password)
    if strength not in {"Medium", "Strong"}:
        raise IdentityValidationError("Password must be at least Medium strength")

    return {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": dob,
        "place_of_birth": _required(data, "place_of_birth", "Place of birth"),
        "nationality": _required(data, "nationality", "Nationality"),
        "gender": _required(data, "gender", "Gender"),
        "personal_email": personal_email,
        "phone_number": phone_number,
        "user_type": user_type,
        "password_hash": generate_password_hash(password),  # store hashed password
    }


def _apply_student_data(profile, data):
    profile.student_category = _required(data, "student_category", "Student category")
    profile.national_id_number = _required(data, "national_id_number", "National ID number")
    profile.high_school_diploma_type = _required(
        data, "high_school_diploma_type", "High school diploma type"
    )
    profile.high_school_diploma_year = int(
        _required(data, "high_school_diploma_year", "High school diploma year")
    )
    profile.high_school_honors = str(data.get("high_school_honors", "")).strip() or None
    profile.major_program = _required(data, "major_program", "Major/program")
    profile.entry_year = int(_required(data, "entry_year", "Entry year"))
    profile.academic_status = _required(data, "academic_status", "Academic status")
    profile.faculty = _required(data, "faculty", "Faculty")
    profile.department = _required(data, "department", "Department")
    profile.group_name = str(data.get("group_name", "")).strip() or None
    profile.scholarship_status = str(data.get("scholarship_status", "false")).lower() in {
        "1", "true", "yes", "on",
    }


def _apply_faculty_data(profile, data):
    profile.faculty_category = _required(data, "faculty_category", "Faculty category")
    profile.rank = _required(data, "rank", "Rank")
    profile.employment_category = _required(data, "employment_category", "Employment category")
    profile.appointment_start_date = _parse_date(
        _required(data, "appointment_start_date", "Appointment start date"),
        "Appointment start date",
    )
    profile.primary_department = _required(data, "primary_department", "Primary department")
    profile.secondary_departments = str(data.get("secondary_departments", "")).strip() or None
    profile.office_building = str(data.get("office_building", "")).strip() or None
    profile.office_floor = str(data.get("office_floor", "")).strip() or None
    profile.office_room_number = str(data.get("office_room_number", "")).strip() or None
    profile.phd_institution = str(data.get("phd_institution", "")).strip() or None
    profile.research_areas = str(data.get("research_areas", "")).strip() or None
    profile.habilitation_supervise_research = str(
        data.get("habilitation_supervise_research", "false")
    ).lower() in {"1", "true", "yes", "on"}
    profile.contract_type = _required(data, "contract_type", "Contract type")
    profile.contract_start_date = _parse_date(
        _required(data, "contract_start_date", "Contract start date"),
        "Contract start date",
    )
    contract_end_raw = str(data.get("contract_end_date", "")).strip()
    profile.contract_end_date = _parse_date(contract_end_raw, "Contract end date") if contract_end_raw else None
    teaching_hours_raw = str(data.get("teaching_hours", "")).strip()
    profile.teaching_hours = int(teaching_hours_raw) if teaching_hours_raw else None


def _apply_staff_data(profile, data):
    profile.staff_category = _required(data, "staff_category", "Staff category")
    profile.assigned_department_service = _required(
        data, "assigned_department_service", "Assigned department/service"
    )
    profile.job_title = _required(data, "job_title", "Job title")
    profile.grade = str(data.get("grade", "")).strip() or None
    profile.date_of_entry_university = _parse_date(
        _required(data, "date_of_entry_university", "Date of entry to university"),
        "Date of entry to university",
    )
    contract_start_raw = str(data.get("contract_start_date", "")).strip()
    contract_end_raw = str(data.get("contract_end_date", "")).strip()
    profile.contract_start_date = (
        _parse_date(contract_start_raw, "Contract start date") if contract_start_raw else None
    )
    profile.contract_end_date = _parse_date(contract_end_raw, "Contract end date") if contract_end_raw else None


def _apply_external_data(profile, data):
    profile.external_category = _required(data, "external_category", "External category")
    profile.organization = str(data.get("organization", "")).strip() or None
    profile.access_notes = str(data.get("access_notes", "")).strip() or None

    access_start_raw = str(data.get("access_start_date", "")).strip()
    access_end_raw = str(data.get("access_end_date", "")).strip()
    class_year_raw = str(data.get("alumni_class_year", "")).strip()

    profile.access_start_date = (
        _parse_date(access_start_raw, "Access start date") if access_start_raw else None
    )
    profile.access_end_date = _parse_date(access_end_raw, "Access end date") if access_end_raw else None
    profile.alumni_class_year = int(class_year_raw) if class_year_raw else None


def _log_change(user_id, change_type, field_name=None, old_value=None, new_value=None, notes=None):
    db.session.add(
        IdentityChangeLog(
            user_id=user_id,
            change_type=change_type,
            field_name=field_name,
            old_value=None if old_value is None else str(old_value),
            new_value=None if new_value is None else str(new_value),
            notes=notes,
        )
    )


def create_identity(data):
    common = _validate_common_payload(data)

    sub_category = None
    if common["user_type"] == "student":
        sub_category = str(data.get("student_category", "")).strip().lower() or None
    if common["user_type"] == "staff":
        sub_category = str(data.get("staff_category", "")).strip().lower() or None
    if common["user_type"] == "external":
        sub_category = str(data.get("external_category", "")).strip().lower() or None

    user = User(**common)
    user.unique_identifier = User.generate_unique_identifier(
        common["user_type"], sub_category=sub_category
    )

    db.session.add(user)
    db.session.flush()

    if common["user_type"] == "student":
        profile = Student(user_id=user.id)
        _apply_student_data(profile, data)
    elif common["user_type"] == "faculty":
        profile = Faculty(user_id=user.id)
        _apply_faculty_data(profile, data)
    elif common["user_type"] == "staff":
        profile = Staff(user_id=user.id)
        _apply_staff_data(profile, data)
    else:
        profile = External(user_id=user.id)
        _apply_external_data(profile, data)

    db.session.add(profile)
    _log_change(user.id, "create", notes="Identity created")
    db.session.commit()
    return user


def update_identity(user, data):
    common = _validate_common_payload(data, user_id=user.id)

    tracked_fields = [
        "first_name",
        "last_name",
        "date_of_birth",
        "place_of_birth",
        "nationality",
        "gender",
        "personal_email",
        "phone_number",
        "password_hash",  # keep mybranch changes
    ]

    for field in tracked_fields:
        old_value = getattr(user, field)
        new_value = common[field]
        if old_value != new_value:
            setattr(user, field, new_value)
            _log_change(user.id, "update", field_name=field, old_value=old_value, new_value=new_value)

    if user.user_type == "student":
        _apply_student_data(user.student_profile, data)
    elif user.user_type == "faculty":
        _apply_faculty_data(user.faculty_profile, data)
    elif user.user_type == "staff":
        _apply_staff_data(user.staff_profile, data)
    else:
        _apply_external_data(user.external_profile, data)

    db.session.commit()
    return user


def transition_identity_status(user, new_status):
    old_status = user.identity_status
    user.transition_status(new_status)
    _log_change(
        user.id,
        "status_change",
        field_name="identity_status",
        old_value=old_status,
        new_value=new_status,
    )
    db.session.commit()


def search_identities(search_text=None, user_type=None, status=None, year=None):
    query = User.query

    if search_text:
        like = f"%{search_text.strip()}%"
        query = query.filter(
            db.or_(
                User.unique_identifier.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.personal_email.ilike(like),
            )
        )

    if user_type:
        query = query.filter(User.user_type == user_type)

    if status:
        query = query.filter(User.identity_status == status)

    if year:
        query = query.filter(db.extract("year", User.created_at) == int(year))

    return query.order_by(User.created_at.desc()).all()

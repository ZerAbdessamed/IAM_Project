from app import db


class Student(db.Model):
    """Student-specific data linked to a base user identity."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    # Categorization
    student_category = db.Column(
        db.String(32), nullable=False
    )  # undergraduate, continuing_education, phd, international_exchange

    # Academic information
    national_id_number = db.Column(db.String(64), nullable=False)
    high_school_diploma_type = db.Column(db.String(100), nullable=False)
    high_school_diploma_year = db.Column(db.Integer, nullable=False)
    high_school_honors = db.Column(db.String(100), nullable=True)
    major_program = db.Column(db.String(150), nullable=False)
    entry_year = db.Column(db.Integer, nullable=False)
    academic_status = db.Column(
        db.String(24), nullable=False, default="active"
    )  # active, suspended, graduated, expelled
    faculty = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=False)
    group_name = db.Column(db.String(64), nullable=True)

    # Financial information
    scholarship_status = db.Column(db.Boolean, nullable=False, default=False)

    # Specific to PhD and exchange profiles
    supervisor_name = db.Column(db.String(150), nullable=True)
    expected_duration_years = db.Column(db.Integer, nullable=True)
    temporary_stay_months = db.Column(db.Integer, nullable=True)

    user = db.relationship("User", back_populates="student_profile")

    def __repr__(self):
        return f"<Student user_id={self.user_id} category={self.student_category}>"

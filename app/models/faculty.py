from app import db


class Faculty(db.Model):
    """Faculty-specific data linked to a base user identity."""

    __tablename__ = "faculties"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    # Categorization
    faculty_category = db.Column(
        db.String(32), nullable=False
    )  # tenured, adjunct_part_time, visiting_researcher

    # Professional information
    rank = db.Column(db.String(80), nullable=False)
    employment_category = db.Column(db.String(80), nullable=False)
    appointment_start_date = db.Column(db.Date, nullable=False)
    primary_department = db.Column(db.String(120), nullable=False)
    secondary_departments = db.Column(db.Text, nullable=True)
    office_building = db.Column(db.String(80), nullable=True)
    office_floor = db.Column(db.String(32), nullable=True)
    office_room_number = db.Column(db.String(32), nullable=True)
    phd_institution = db.Column(db.String(150), nullable=True)
    research_areas = db.Column(db.Text, nullable=True)
    habilitation_supervise_research = db.Column(db.Boolean, nullable=False, default=False)

    # Contract information
    contract_type = db.Column(db.String(80), nullable=False)
    contract_start_date = db.Column(db.Date, nullable=False)
    contract_end_date = db.Column(db.Date, nullable=True)
    teaching_hours = db.Column(db.Integer, nullable=True)

    user = db.relationship("User", back_populates="faculty_profile")

    def __repr__(self):
        return f"<Faculty user_id={self.user_id} category={self.faculty_category}>"

from app import db


class Staff(db.Model):
    """Staff-specific data linked to a base user identity."""

    __tablename__ = "staff_members"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    # Categorization
    staff_category = db.Column(
        db.String(32), nullable=False
    )  # administrative, technical, temporary

    # Staff data
    assigned_department_service = db.Column(db.String(120), nullable=False)
    job_title = db.Column(db.String(120), nullable=False)
    grade = db.Column(db.String(64), nullable=True)
    date_of_entry_university = db.Column(db.Date, nullable=False)

    # Contract fields (important for temporary staff)
    contract_start_date = db.Column(db.Date, nullable=True)
    contract_end_date = db.Column(db.Date, nullable=True)

    user = db.relationship("User", back_populates="staff_profile")

    def __repr__(self):
        return f"<Staff user_id={self.user_id} category={self.staff_category}>"

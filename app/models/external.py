from app import db


class External(db.Model):
    """External-specific data linked to a base user identity."""

    __tablename__ = "externals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    # Categorization
    external_category = db.Column(
        db.String(32), nullable=False
    )  # contractor_vendor, alumni

    organization = db.Column(db.String(150), nullable=True)
    access_notes = db.Column(db.Text, nullable=True)
    access_start_date = db.Column(db.Date, nullable=True)
    access_end_date = db.Column(db.Date, nullable=True)
    alumni_class_year = db.Column(db.Integer, nullable=True)

    user = db.relationship("User", back_populates="external_profile")

    def __repr__(self):
        return f"<External user_id={self.user_id} category={self.external_category}>"

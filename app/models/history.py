from app import db


class IdentityChangeLog(db.Model):
    """Tracks user profile and status changes for auditability in Project 1."""

    __tablename__ = "identity_change_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    change_type = db.Column(db.String(32), nullable=False)  # create, update, status_change
    field_name = db.Column(db.String(100), nullable=True)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    changed_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    user = db.relationship("User", back_populates="change_logs")

    def __repr__(self):
        return f"<IdentityChangeLog user_id={self.user_id} change_type={self.change_type}>"

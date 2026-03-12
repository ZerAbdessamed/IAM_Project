from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class AdminAccount(UserMixin, db.Model):
    """Simple admin account used for initial authentication bootstrap."""

    __tablename__ = "admin_accounts"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active_flag = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    @property
    def is_active(self):
        return self.is_active_flag

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def get_id(self):
        return f"admin:{self.id}"

    def __repr__(self):
        return f"<AdminAccount username={self.username}>"

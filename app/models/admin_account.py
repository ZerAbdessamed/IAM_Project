from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
import pyotp

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

    totp_secret = db.Column(db.String(32), nullable=True)
    mfa_enabled = db.Column(db.Boolean, default=False)
    manage_mfa_enabled = db.Column(db.Boolean, default=True)
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


    def generate_totp_secret(self):
        """Generate new secret for MFA"""
        self.totp_secret = pyotp.random_base32()

    def get_totp_uri(self):
        """Generate QR Code URI"""
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email,
            issuer_name="University IAM Admin"
        )

    def verify_totp(self, code):
        """Verify MFA code"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code)

    def __repr__(self):
        return f"<AdminAccount username={self.username}>"
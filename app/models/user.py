from datetime import date
import pyotp
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from app import db



class IdentitySequence(db.Model):
    """Tracks running sequence numbers used for unique identifier generation."""
    __tablename__ = "identity_sequences"

    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(8), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    current_value = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("prefix", "year", name="uq_identity_sequence_prefix_year"),
    )


class User(UserMixin, db.Model):
    """Base identity model containing common data for all individuals."""
    __tablename__ = "users"

    ALLOWED_IDENTITY_STATUSES = {"pending", "active", "suspended", "inactive", "archived"}
    ALLOWED_TRANSITIONS = {
        "pending": {"active"},
        "active": {"suspended", "inactive"},
        "suspended": {"active"},
        "inactive": {"active" ,"archived"},
        "archived": set(),
    }

    id = db.Column(db.Integer, primary_key=True)
    unique_identifier = db.Column(db.String(16), unique=True, nullable=False, index=True)

    
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    place_of_birth = db.Column(db.String(120), nullable=False)
    nationality = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(24), nullable=False)
    personal_email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    
    failed_login_attempts = db.Column(db.Integer, default=0)
    lockout_until = db.Column(db.DateTime, nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)

   
    totp_secret = db.Column(db.String(32), nullable=True)
    mfa_enabled = db.Column(db.Boolean, default=False)
    first_login = db.Column(db.Boolean, default=True)
    # Identity lifecycle
    user_type = db.Column(db.String(24), nullable=False)
    identity_status = db.Column(db.String(24), nullable=False, default="pending")

    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False
    )

    # Relationships
    student_profile = db.relationship(
        "Student", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    faculty_profile = db.relationship(
        "Faculty", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    staff_profile = db.relationship(
        "Staff", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    external_profile = db.relationship(
        "External", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    change_logs = db.relationship(
        "IdentityChangeLog", back_populates="user", cascade="all, delete-orphan"
    )

   

 

    def get_reset_token(self):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800): 
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
        except:
            return None
        return User.query.get(data['user_id'])

    @property
    def is_active(self):
        return self.identity_status == "active"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_id(self):
        return f"user:{self.id}"

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    

    def generate_totp_secret(self):
        """Generate a new TOTP secret"""
        self.totp_secret = pyotp.random_base32()

    def get_totp_uri(self):
        """Generate URI for QR Code (Google Authenticator)"""
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.personal_email,
            issuer_name="University IAM"
        )

    def verify_totp(self, code):
        """Verify TOTP code"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        print("#"*150)
        print(code)
        print(totp.verify(code))
        return totp.verify(code)

 

    @staticmethod
    def get_prefix_for_category(user_type, sub_category=None):
        if user_type == "student" and sub_category == "phd":
            return "PHD"
        if user_type == "staff" and sub_category == "temporary":
            return "TMP"

        default_prefixes = {
            "student": "STU",
            "faculty": "FAC",
            "staff": "STF",
            "external": "EXT",
        }
        return default_prefixes.get(user_type)

    @classmethod
    def generate_unique_identifier(cls, user_type, sub_category=None, year=None):
        generation_year = year or date.today().year
        prefix = cls.get_prefix_for_category(user_type, sub_category)

        if not prefix:
            raise ValueError("Invalid user type/sub-category")

        seq = IdentitySequence.query.filter_by(prefix=prefix, year=generation_year).first()

        if seq is None:
            seq = IdentitySequence(prefix=prefix, year=generation_year, current_value=0)
            db.session.add(seq)

        seq.current_value += 1

        return f"{prefix}{generation_year}{seq.current_value:05d}"


    @classmethod
    def is_valid_transition(cls, from_status, to_status):
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, set())

    def can_transition_to(self, new_status):
        return self.is_valid_transition(self.identity_status, new_status)

    def transition_status(self, new_status):
        if new_status not in self.ALLOWED_IDENTITY_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")

        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid transition from {self.identity_status} to {new_status}"
            )

        self.identity_status = new_status

    def __repr__(self):
        return f"<User id={self.id} uid={self.unique_identifier} type={self.user_type}>"
    
    
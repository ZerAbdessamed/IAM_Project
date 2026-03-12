from datetime import date

from flask_login import UserMixin

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
        "inactive": {"archived"},
        "archived": set(),
    }

    id = db.Column(db.Integer, primary_key=True)
    unique_identifier = db.Column(db.String(16), unique=True, nullable=False, index=True)

    # Common data for all individuals
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    place_of_birth = db.Column(db.String(120), nullable=False)
    nationality = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(24), nullable=False)
    personal_email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)

    # Identity categorization and lifecycle
    user_type = db.Column(db.String(24), nullable=False)  # student, faculty, staff, external
    identity_status = db.Column(db.String(24), nullable=False, default="pending")

    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False
    )

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

    @property
    def is_active(self):
        """Compatibility helper for Flask-Login and account state checks."""
        return self.identity_status == "active"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_id(self):
        return f"user:{self.id}"

    @staticmethod
    def get_prefix_for_category(user_type, sub_category=None):
        """Return the correct identifier prefix based on type/sub-category."""
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
        """Generate identifier in [TYPE][YEAR][NUMBER] format with 5-digit sequence."""
        generation_year = year or date.today().year
        prefix = cls.get_prefix_for_category(user_type, sub_category)
        if not prefix:
            raise ValueError("Invalid user type/sub-category for identifier generation")

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
        """Apply lifecycle transition only if it is allowed by project rules."""
        if new_status not in self.ALLOWED_IDENTITY_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid transition from {self.identity_status} to {new_status}"
            )
        self.identity_status = new_status

    def __repr__(self):
        return f"<User id={self.id} uid={self.unique_identifier} type={self.user_type}>"

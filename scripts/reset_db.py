import argparse
import importlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app, db
from app.models.user import User
from app.models import AdminAccount
from werkzeug.security import generate_password_hash


def ensure_database_exists(database_uri: str) -> None:
    """Create the target database when using MySQL and it does not exist yet."""
    url = make_url(database_uri)
    backend = url.get_backend_name()

    if not backend.startswith("mysql"):
        return

    database_name = url.database
    if not database_name:
        return

    server_url = url.set(database=None)
    engine = create_engine(server_url)
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            connection.commit()
    finally:
        engine.dispose()


def reset_database(flask_env: str) -> None:
    """Drop all tables, recreate them, and optionally create a default admin."""
    app = create_app(flask_env)

    with app.app_context():
       
        importlib.import_module("app.models")

        database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        ensure_database_exists(database_uri)

       
        db.drop_all()
        db.create_all()

        
        engine = db.get_engine()
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE users MODIFY password_hash VARCHAR(1024) NOT NULL"
            ))
            conn.commit()

        
        if not AdminAccount.query.first():
            default_admin = AdminAccount(
                username="admin",
                email="admin@example.com",
                full_name="Super Admin",
                password_hash=generate_password_hash("Admin123!"),
                is_active_flag=True,
                mfa_enabled=False,
            )
            db.session.add(default_admin)
            db.session.commit()
            print("Default admin created: username='admin', password='Admin123!'")

    print(f"Fresh database created successfully for environment: {flask_env}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Drop and recreate all IAM database tables."
    )
    parser.add_argument(
        "--env",
        default=os.getenv("FLASK_ENV", "development"),
        choices=["default", "development", "testing", "production"],
        help="Flask environment config to use.",
    )
    args = parser.parse_args()

    reset_database(args.env)


if __name__ == "__main__":
    main()
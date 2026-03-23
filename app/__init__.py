from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flasgger import Swagger
from dotenv import load_dotenv
import importlib

from app.config import config_by_name

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/api/doc/apispec.json',
            "rule_filter": lambda rule: rule.rule.startswith('/api'),
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/doc"
}

swagger_template = {
    "info": {
        "title": "University IAM API",
        "description": "Identity and Access Management System API",
        "version": "1.0.0",
        "contact": {
            "name": "IAM Support",
            "email": "support@university.edu"
        }
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer {token}'"
        }
    },
    "tags": [
        {"name": "Identity", "description": "Identity management operations"},
        {"name": "Authentication", "description": "Authentication operations"},
        {"name": "Admin", "description": "Administrative operations"}
    ],
    "definitions": {
        "User": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "unique_identifier": {"type": "string"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "date_of_birth": {"type": "string", "format": "date"},
                "place_of_birth": {"type": "string"},
                "nationality": {"type": "string"},
                "gender": {"type": "string"},
                "personal_email": {"type": "string"},
                "phone_number": {"type": "string"},
                "user_type": {"type": "string"},
                "identity_status": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"},
                "profile": {"type": "object"},
            },
        },
        "IdentityCreateRequest": {
            "type": "object",
            "required": [
                "user_type",
                "first_name",
                "last_name",
                "date_of_birth",
                "place_of_birth",
                "nationality",
                "gender",
                "personal_email",
                "phone_number",
            ],
            "properties": {
                "user_type": {"type": "string", "enum": ["student", "faculty", "staff", "external"]},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "date_of_birth": {"type": "string", "format": "date"},
                "place_of_birth": {"type": "string"},
                "nationality": {"type": "string"},
                "gender": {"type": "string"},
                "personal_email": {"type": "string"},
                "phone_number": {"type": "string"},
            },
        },
        "IdentityListResponse": {
            "type": "object",
            "properties": {
                "identities": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/User"},
                },
            },
        },
        "IdentityResponse": {
            "type": "object",
            "properties": {
                "identity": {"$ref": "#/definitions/User"},
            },
        },
        "MessageResponse": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
        },
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
            },
        },
        "AdminRegisterRequest": {
            "type": "object",
            "required": ["username", "email", "full_name", "password"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string"},
                "full_name": {"type": "string"},
                "password": {"type": "string"},
                "bootstrap_key": {"type": "string"},
            },
        },
        "AdminLoginRequest": {
            "type": "object",
            "required": ["username_or_email", "password"],
            "properties": {
                "username_or_email": {"type": "string"},
                "password": {"type": "string"},
            },
        },
        "AdminResponse": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "username": {"type": "string"},
                "email": {"type": "string"},
                "full_name": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "AdminAuthResponse": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "admin": {"$ref": "#/definitions/AdminResponse"},
            },
        },
        "IdentityExamplesResponse": {
            "type": "object",
            "properties": {
                "student": {"$ref": "#/definitions/IdentityCreateRequest"},
                "faculty": {"$ref": "#/definitions/IdentityCreateRequest"},
                "staff": {"$ref": "#/definitions/IdentityCreateRequest"},
                "external": {"$ref": "#/definitions/IdentityCreateRequest"},
            },
        },
    },
}

def create_app(config_name='default'):
    """Application factory."""
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))
    
    

    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='iam.university.project@gmail.com',
        MAIL_PASSWORD='hkjeoeeqqceoehwz'
    )



    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.admin_account import AdminAccount
        from app.models.user import User

        if user_id.startswith('admin:'):
            return AdminAccount.query.get(int(user_id.split(':', 1)[1]))
        if user_id.startswith('user:'):
            return User.query.get(int(user_id.split(':', 1)[1]))

        # Backward compatibility for plain numeric IDs.
        if user_id.isdigit():
            return User.query.get(int(user_id))
        return None
    
    # Register blueprints (UI)
    from app.routes import register_blueprints
    register_blueprints(app)
    
    # Register API blueprints
    from app.api import register_api_blueprints
    register_api_blueprints(app)
    
    # Initialize Swagger
    Swagger(app, config=swagger_config, template=swagger_template)
    
    # Create database tables for quick local setup.
    with app.app_context():
        # Import model package so SQLAlchemy metadata includes all tables.
        importlib.import_module('app.models')
        db.create_all()
    
    return app

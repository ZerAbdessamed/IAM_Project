from flask import Blueprint

# API Blueprints
api_identity_bp = Blueprint('api_identity', __name__, url_prefix='/api/identity')
api_auth_bp = Blueprint('api_auth', __name__, url_prefix='/api/auth')
api_admin_bp = Blueprint('api_admin', __name__, url_prefix='/api/admin')


def register_api_blueprints(app):
    """Register all API blueprints."""
    from app.api import identity, auth, admin
    
    app.register_blueprint(api_identity_bp)
    app.register_blueprint(api_auth_bp)
    app.register_blueprint(api_admin_bp)

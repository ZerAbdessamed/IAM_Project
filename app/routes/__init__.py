from flask import Blueprint

# Create blueprints
main_bp = Blueprint('main', __name__)
identity_bp = Blueprint('identity', __name__, url_prefix='/identity')
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def register_blueprints(app):
    """Register all blueprints with the app."""
    from app.routes import main, identity, auth, admin
    
    app.register_blueprint(main_bp)
    app.register_blueprint(identity_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

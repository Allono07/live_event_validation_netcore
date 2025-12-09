"""Flask application factory."""
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from config.database import db, init_db

socketio = SocketIO()


def create_app(config_name='development'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    from config.config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth_email.login_email'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.controllers.auth_email_controller import auth_bp as auth_email_bp
    from app.controllers.dashboard_controller import dashboard_bp
    from app.controllers.api_controller import api_bp
    from app.controllers.push_notification_controller import push_bp
    
    app.register_blueprint(auth_email_bp)  # Uses its own url_prefix='/auth'
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(push_bp, url_prefix='/')
    
    # Import WebSocket handlers
    from app.controllers import websocket_controller
    
    # Initialize database tables
    with app.app_context():
        from app.models import user, app as app_model, validation_rule, log_entry, fcm_token, firebase_credential, otp
        db.create_all()
    
    return app

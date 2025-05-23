from flask import Flask, jsonify
from flask_cors import CORS
from backend.models import db
from backend.bp.auth import auth_bp, login_manager
from backend.bp.main import main_bp
from backend.bp.journal import journal_bp
from backend.bp.analytics import analytics_bp
from backend.bp.chat import chat_bp
import os

# Import configurations and validation functions
from backend.config import config
from backend.utils.env_validation import validate_environment_variables
from backend.utils.register_error import register_error_handlers
from backend.utils.security_headers import configure_security_headers

# Add rate limiting to control how often a user can make requests to the API
# This helps protect against abuse and excessive traffic.
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def setup_rate_limiting(app):
    """Set up rate limiting with more granular controls."""
    
    # Use Redis in production, memory in development
    storage_uri = os.getenv('REDIS_URL', "memory://")
    
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["1000 per day", "100 per hour"],
        storage_uri=storage_uri,
        headers_enabled=True  # Add rate limit headers to responses
    )
    
    # Apply specific rate limits
    limiter.limit("5/minute")(auth_bp)  # More restrictive for auth
    limiter.limit("3/minute")(analytics_bp)  # AI calls are expensive
    limiter.limit("20/minute")(chat_bp)  # Allow more chat messages
    limiter.limit("50/minute")(journal_bp)  # Allow normal journaling
    
    return limiter

def create_app(config_name=None):
    """Create and configure the Flask application using the app factory pattern."""
    
    # Determine configuration
    config_name = config_name or os.getenv('FLASK_CONFIG', 'default')
    
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Validate environment in production
    if config_name == 'production':
        try:
            validate_environment_variables()
        except ValueError as e:
            app.logger.error(f"Configuration error: {e}")
            raise
    
    # Ensure instance path exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError as e:
        app.logger.warning(f"Could not create instance path: {e}")
    
    # Configure CORS
    cors_origins = app.config.get('CORS_ORIGINS', ["http://localhost:5173"])
    CORS(app, 
         origins=cors_origins,
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'])
    
    # Set up rate limiting
    limiter = setup_rate_limiting(app)
    
    # Configure security headers
    configure_security_headers(app)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = "strong"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(chat_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Failed to create database tables: {e}")
            raise
    
    app.logger.info(f"Application created with {config_name} configuration")
    return app
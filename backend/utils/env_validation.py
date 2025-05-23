import os
import logging

def validate_environment_variables():
    """Validate required environment variables are set."""
    required_vars = [
        'SQLALCHEMY_DATABASE_URI',
        'SECRET_KEY',
        'LOCAL_DOMAIN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def get_database_uri():
    """Get database URI with fallback for development."""
    db_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
    if not db_uri:
        # Fallback for development
        return 'sqlite:///journal_app.db'
    return db_uri

def get_secret_key():
    """Get secret key with validation."""
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        if os.getenv('FLASK_ENV') == 'production':
            raise ValueError("SECRET_KEY must be set in production")
        else:
            # Generate a warning for development
            import secrets
            logging.warning("SECRET_KEY not set, using generated key for development")
            return secrets.token_urlsafe(32)
    return secret_key
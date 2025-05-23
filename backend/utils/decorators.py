from functools import wraps
from flask import jsonify
from flask_login import current_user

def api_login_required(f):
    """Custom login required decorator that returns JSON instead of redirecting."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function
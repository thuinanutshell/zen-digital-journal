from backend.models import db, User
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required
from datetime import datetime
from backend.utils.decorators import api_login_required

# Define the Blueprint extension for authentication feature (modular)
# Organize a group of related routes, views, templates, and static files
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
login_manager = LoginManager()

def validate_registration_data(data):
    """Validate registration input data"""
    errors = []
    
    if not data.get('username') or len(data['username'].strip()) < 3:
        errors.append("Username must be at least 3 characters")
    
    if not data.get('email') or '@' not in data['email']:
        errors.append("Valid email is required")
    
    if not data.get('password') or len(data['password']) < 8:
        errors.append("Password must be at least 8 characters")
    
    return errors

@login_manager.user_loader
def load_user(user_id):
    """Callback function to reload user object from user ID stored in the session cookie.

    Args:
        user_id (str): The user ID from the session cookie

    Returns:
        User: The User object if found, None otherwise
    """
    return User.query.get(int(user_id))

@auth_bp.route('/register', methods=['POST'])
def register():
    """Function to register a new account to the web
    """
    # Check content type first
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    # Get all the information that the user entered
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate input
    validation_errors = validate_registration_data(data)
    if validation_errors:
        return jsonify({"errors": validation_errors}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Check if the user exists or not 
    # Username and email have to be unique
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409
    elif User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409
    
    # Hash user's password for security purpose
    hashed_password = generate_password_hash(password)
    # Create a new user object with username, email, hashed password
    new_user = User(username=username, email=email, password=hashed_password)
    
    try:
        # Add new user record to the database
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"User registration error: {str(e)}")
        return jsonify({"error": "Failed to register new user"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Function to log in user
    """
    # Check content type first
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    # Get user's information for login (identifier can be email or username)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    identifier = data.get('identifier', '').strip()
    password = data.get('password', '')
    
    if not identifier or not password:
        return jsonify({"error": "Both identifier and password are required"}), 400
    
    # Check if user exists in the database
    user = User.query.filter((User.username==identifier) | (User.email==identifier)).first()
    if user and check_password_hash(user.password, password):
        user.last_activity_date = datetime.utcnow() # update user's last activity to compute user's streak
        login_user(user)
        current_app.logger.info(f"User logged in: {user.username}")
        return jsonify({"message": "Logged in successfully",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email}})
    else:
        current_app.logger.warning(f"Failed login attempt for identifier: {identifier}")
        return jsonify({"error": "Invalid credentials"}), 401

@auth_bp.route('/logout', methods=['POST'])
@api_login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200
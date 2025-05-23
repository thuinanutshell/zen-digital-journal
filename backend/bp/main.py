from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return jsonify({"message": "Welcome to the API root"})

@main_bp.route('/profile')
@login_required
def profile():
    user_data = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }
    return jsonify(user_data)

from backend.models import db, User, Journal
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

# Libraries for multimodal input transcription
import easyocr
import os
import uuid
import tempfile
import datetime
from werkzeug.utils import secure_filename
import bleach

# Define the blueprint for journal feature with a prefix of '/journal'
journal_bp = Blueprint('journal', __name__, url_prefix='/journal')

# Initialize OCR reader once (consider lazy loading in production)
ocr_reader = easyocr.Reader(['en'])

def allowed_image_file(filename):
    """Validate if uploaded file has an allowed image extension."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

def allowed_audio_file(filename):
    """Validate if uploaded file has an allowed audio extension."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in {'wav', 'mp3', 'm4a'}

def sanitize_text_input(text, max_length=10000):
    """Sanitize and validate text input to prevent XSS attacks."""
    if not text:
        return None
    
    # Remove HTML tags and limit length
    clean_text = bleach.clean(text.strip(), tags=[], strip=True)
    return clean_text[:max_length] if len(clean_text) > max_length else clean_text

def update_user_streak(user, now):
    """Update user's streak based on their last activity.
    
    Args:
        user: The current user object
        now: Current datetime
    
    Returns:
        dict or None: Error message if entry already created today, None otherwise
    """
    if user.last_activity_date:
        if user.last_activity_date:
            # Only check for existing entries if last_activity was from an actual journal entry
            # Check if there's already a journal entry for today
            today_entries = Journal.query.filter(
                Journal.user_id == user.id,
                Journal.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
                Journal.deleted_at.is_(None)
            ).count()
            
        if today_entries > 0:
            return {"error": "Entry already created today"}
        
        # Calculate days since last activity (comparing dates, not raw time)
        last_date = user.last_activity_date.date()
        today = now.date()
        days_diff = (today - last_date).days
        
        if days_diff == 0:
            return {"error": "Entry already created today"}
        elif days_diff == 1:
            # Continue streak - consecutive day
            user.current_streak += 1
        else:
            # Reset streak if more than 1 day gap
            user.current_streak = 1
    else:
        # First entry ever
        user.current_streak = 1
    
    # Update longest streak if current exceeds it
    user.longest_streak = max(user.current_streak, user.longest_streak)
    user.last_activity_date = now
    return None

def validate_create_entry_data(form_data):
    """Validate form data for creating journal entry.
    
    Returns:
        tuple: (errors_list, cleaned_data_dict)
    """
    errors = []
    
    # Validate and sanitize prompt
    prompt = sanitize_text_input(form_data.get('prompt'))
    if not prompt:
        errors.append("Prompt is required and cannot be empty")
    
    # Validate modality
    modality = form_data.get('modality', 'text').lower()
    if modality not in ['text', 'image', 'audio']:
        errors.append("Invalid modality. Must be 'text', 'image', or 'audio'")
    
    # Validate and sanitize tag
    tag = sanitize_text_input(form_data.get('tag', ''), max_length=150)
    
    return errors, {
        'prompt': prompt,
        'modality': modality,
        'tag': tag
    }

@journal_bp.route('/create', methods=['POST'])
@login_required
def create_entry():
    """Create a journal entry with support for multiple input modalities.
    
    Supports text, image (OCR), and audio input.
    Implements streak tracking and prevents duplicate daily entries.
    """
    now = datetime.datetime.utcnow()  # Use UTC for consistency
    
    # Update user streak and check for duplicate daily entry
    streak_error = update_user_streak(current_user, now)
    if streak_error:
        return jsonify(streak_error), 400
    
    # Validate input data
    validation_errors, cleaned_data = validate_create_entry_data(request.form)
    if validation_errors:
        return jsonify({"errors": validation_errors}), 400
    
    prompt = cleaned_data['prompt']
    modality = cleaned_data['modality']
    tag = cleaned_data['tag']
    answer = None
    
    try:
        if modality == 'text':
            answer = sanitize_text_input(request.form.get('answer'))
            if not answer:
                return jsonify({"error": "Answer text is required for text modality"}), 400
        
        elif modality == 'image':
            # Validate file upload
            if 'file' not in request.files:
                return jsonify({"error": "No image file uploaded"}), 400
            
            image_file = request.files['file']
            if image_file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            if not allowed_image_file(image_file.filename):
                return jsonify({"error": "Invalid image file format. Allowed: png, jpg, jpeg"}), 400
            
            # Check file size (read content to get actual size)
            image_file.seek(0, os.SEEK_END)  # Move to end
            file_size = image_file.tell()    # Get position (file size)
            image_file.seek(0)               # Reset to beginning
            
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                return jsonify({"error": "File size exceeds 10MB limit"}), 400
            
            if file_size == 0:
                return jsonify({"error": "Uploaded file is empty"}), 400
            
            # Process image with OCR
            filename = secure_filename(image_file.filename)
            unique_filename = f"{str(uuid.uuid4())}_{filename}"
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = os.path.join(temp_dir, unique_filename)
                
                try:
                    image_file.save(temp_path)
                    
                    # Perform OCR
                    result = ocr_reader.readtext(temp_path)
                    extracted_texts = [text[1] for text in result if text[1].strip()]
                    answer = " ".join(extracted_texts)
                    
                    if not answer or not answer.strip():
                        return jsonify({"error": "No readable text found in the image"}), 400
                        
                except Exception as ocr_error:
                    current_app.logger.error(f"OCR processing error: {str(ocr_error)}")
                    return jsonify({"error": "Failed to process the image. Please try a clearer image."}), 500

        elif modality == 'audio':
            # Validate audio file upload
            if 'file' not in request.files:
                return jsonify({"error": "No audio file uploaded"}), 400
            
            audio_file = request.files['file']
            if audio_file.filename == '':
                return jsonify({"error": "No audio file selected"}), 400
            
            if not allowed_audio_file(audio_file.filename):
                return jsonify({"error": "Invalid audio format. Allowed: wav, mp3, m4a"}), 400
                
            return jsonify({"error": "Audio processing feature coming soon"}), 501
        
        # Final validation of answer length
        if answer and len(answer) > 10000:
            answer = answer[:10000]
            current_app.logger.warning(f"Answer truncated to 10000 characters for user {current_user.id}")
        
        # Create journal entry
        entry = Journal(
            prompt=prompt,
            answer=answer,
            modality=modality,
            tag=tag,
            user_id=current_user.id
        )
        
        # Save to database
        db.session.add(entry)
        db.session.commit()
        
        current_app.logger.info(f"Journal entry created: ID {entry.id}, User {current_user.id}")
        
        return jsonify({
            "message": "Entry created successfully",
            "entry": {
                "id": entry.id,
                "prompt": entry.prompt,
                "answer": answer,
                "modality": modality,
                "tag": tag,
                "created_at": entry.created_at.isoformat() if hasattr(entry, 'created_at') else None
            },
            "streak": {
                "current_streak": current_user.current_streak,
                "longest_streak": current_user.longest_streak
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating journal entry: {str(e)}")
        return jsonify({"error": "An unexpected error occurred while creating the entry"}), 500

@journal_bp.route('/entries', methods=['GET'])
@login_required
def get_all_entries():
    """Retrieve all journal entries for the current user with pagination."""
    try:
        # Get and validate pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:  # Limit per_page to prevent abuse
            per_page = 10
        
        # Query with pagination
        # This helps loading entries in pages
        pagination = Journal.query.filter_by(user_id=current_user.id) \
                        .filter(Journal.deleted_at.is_(None)) \
                        .order_by(Journal.created_at.desc()) \
                        .paginate(page=page, per_page=per_page, error_out=False)
        
        entries_list = []
        for entry in pagination.items:
            entries_list.append({
                "id": entry.id,
                "prompt": entry.prompt,
                "answer": entry.answer,
                "tag": entry.tag,
                "modality": entry.modality,
                "created_at": entry.created_at.isoformat() if hasattr(entry, 'created_at') else None,
                "updated_at": entry.updated_at.isoformat() if hasattr(entry, 'updated_at') else None
            })
        
        return jsonify({
            "entries": entries_list,
            "pagination": {
                "total": pagination.total,
                "pages": pagination.pages,
                "current_page": page,
                "per_page": per_page,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error retrieving journal entries: {str(e)}")
        return jsonify({"error": "Failed to retrieve entries"}), 500

@journal_bp.route('/entries/<string:tag_name>', methods=['GET'])
@login_required
def get_entries_by_tag(tag_name):
    """Retrieve journal entries filtered by tag with pagination."""
    try:
        # Sanitize tag name
        clean_tag = sanitize_text_input(tag_name, max_length=150)
        if not clean_tag:
            return jsonify({"error": "Invalid tag name"}), 400
        
        # Get and validate pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:
            per_page = 10
        
        # Query with pagination and tag filter
        pagination = Journal.query.filter_by(tag=clean_tag, user_id=current_user.id) \
                        .filter(Journal.deleted_at.is_(None)) \
                        .order_by(Journal.created_at.desc()) \
                        .paginate(page=page, per_page=per_page, error_out=False)
        
        entries_list = []
        for entry in pagination.items:
            entries_list.append({
                "id": entry.id,
                "prompt": entry.prompt,
                "answer": entry.answer,
                "tag": entry.tag,
                "modality": entry.modality,
                "created_at": entry.created_at.isoformat() if hasattr(entry, 'created_at') else None,
                "updated_at": entry.updated_at.isoformat() if hasattr(entry, 'updated_at') else None
            })
            
        return jsonify({
            "entries": entries_list,
            "tag": clean_tag,
            "pagination": {
                "total": pagination.total,
                "pages": pagination.pages,
                "current_page": page,
                "per_page": per_page,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error retrieving entries by tag: {str(e)}")
        return jsonify({"error": "Failed to retrieve entries by tag"}), 500

@journal_bp.route('/entry/<int:entry_id>', methods=['GET'])
@login_required
def get_single_entry(entry_id):
    """Retrieve a single journal entry by ID."""
    try:
        # Validate entry_id
        if entry_id <= 0:
            return jsonify({"error": "Invalid entry ID"}), 400
        
        # Retrieve the journal entry
        entry = Journal.query.filter_by(id=entry_id, user_id=current_user.id) \
                           .filter(Journal.deleted_at.is_(None)) \
                           .first()
        
        if not entry:
            return jsonify({"error": "Entry not found or access denied"}), 404
        
        return jsonify({
            "entry": {
                "id": entry.id,
                "prompt": entry.prompt,
                "answer": entry.answer,
                "tag": entry.tag,
                "modality": entry.modality,
                "created_at": entry.created_at.isoformat() if hasattr(entry, 'created_at') else None,
                "updated_at": entry.updated_at.isoformat() if hasattr(entry, 'updated_at') else None
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error retrieving single entry: {str(e)}")
        return jsonify({"error": "Failed to retrieve entry"}), 500

@journal_bp.route('/update/<int:entry_id>', methods=['PUT'])
@login_required
def update_entry(entry_id):
    """Update an existing journal entry."""
    try:
        # Validate entry_id
        if entry_id <= 0:
            return jsonify({"error": "Invalid entry ID"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Find the entry
        entry = Journal.query.filter_by(id=entry_id, user_id=current_user.id) \
                           .filter(Journal.deleted_at.is_(None)) \
                           .first()
        
        if not entry:
            return jsonify({"error": "Entry not found or access denied"}), 404
        
        # Track what was updated
        updated_fields = []
        
        # Update prompt if provided
        if "prompt" in data:
            new_prompt = sanitize_text_input(data["prompt"], max_length=255)
            if not new_prompt:
                return jsonify({"error": "Prompt cannot be empty"}), 400
            entry.prompt = new_prompt
            updated_fields.append("prompt")
        
        # Update answer if provided
        if "answer" in data:
            new_answer = sanitize_text_input(data["answer"], max_length=10000)
            if not new_answer:
                return jsonify({"error": "Answer cannot be empty"}), 400
            entry.answer = new_answer
            updated_fields.append("answer")
        
        # Update tag if provided
        if "tag" in data:
            new_tag = sanitize_text_input(data["tag"], max_length=150)
            entry.tag = new_tag  # Tag can be empty
            updated_fields.append("tag")
        
        if not updated_fields:
            return jsonify({"error": "No valid fields provided for update"}), 400
        
        # Save changes
        db.session.commit()
        
        current_app.logger.info(f"Entry {entry_id} updated by user {current_user.id}: {updated_fields}")
        
        return jsonify({
            "message": "Entry updated successfully",
            "updated_fields": updated_fields,
            "entry": {
                "id": entry.id,
                "prompt": entry.prompt,
                "answer": entry.answer,
                "tag": entry.tag,
                "modality": entry.modality,
                "updated_at": entry.updated_at.isoformat() if hasattr(entry, 'updated_at') else None
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating entry: {str(e)}")
        return jsonify({"error": "Failed to update entry"}), 500

@journal_bp.route('/delete/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_entry(entry_id):
    """Soft delete a journal entry (sets deleted_at timestamp)."""
    try:
        # Validate entry_id
        if entry_id <= 0:
            return jsonify({"error": "Invalid entry ID"}), 400
        
        # Find the entry
        entry = Journal.query.filter_by(id=entry_id, user_id=current_user.id) \
                           .filter(Journal.deleted_at.is_(None)) \
                           .first()
        
        if not entry:
            return jsonify({"error": "Entry not found or access denied"}), 404
        
        # Soft delete - set deleted_at timestamp
        entry.deleted_at = datetime.datetime.utcnow()
        db.session.commit()
        
        current_app.logger.info(f"Entry {entry_id} soft deleted by user {current_user.id}")
        
        return jsonify({"message": "Entry deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting entry: {str(e)}")
        return jsonify({"error": "Failed to delete entry"}), 500

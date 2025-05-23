from backend.models import db, Conversation, Journal
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import os
import google.generativeai as genai
import re
import bleach
from datetime import datetime, timedelta

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# Configure constants for fetching journal entries for new chat context
MAX_JOURNAL_ENTRIES_FOR_CONTEXT = 5
JOURNAL_CONTEXT_DAYS = 30

def validate_message_input(data):
    """Validate and sanitize chat message input."""
    if not data:
        return None, "No data provided"
    
    message = data.get('message', '').strip()
    if not message:
        return None, "Message cannot be empty"
    
    if len(message) > 2000:  # Reasonable message length limit
        return None, "Message too long (maximum 2000 characters)"
    
    # Basic sanitization
    clean_message = bleach.clean(message, tags=[], strip=True)
    if not clean_message:
        return None, "Message contains no valid content"
    
    conversation_id = data.get('conversation_id')
    if conversation_id is not None:
        if not isinstance(conversation_id, int) or conversation_id <= 0:
            return None, "Invalid conversation ID"
    
    return {"message": clean_message, "conversation_id": conversation_id}, None

def sanitize_journal_content_for_ai(text, max_length=150):
    """Sanitize journal content before sending to AI to protect privacy."""
    if not text:
        return ""
    
    # Remove potentially sensitive information
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', text)
    text = re.sub(r'\b\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)\b', '[ADDRESS]', text, flags=re.IGNORECASE)
    
    # Truncate and clean
    text = text[:max_length].strip()
    return text

def format_entries_for_initial_context(entries):
    """Enhanced version with better privacy protection."""
    if not entries:
        return ""
    
    formatted_entries_list = []
    for entry in entries:
        # Use relative dates for privacy (month-day only)
        date_str = entry.created_at.strftime("%m-%d") if hasattr(entry, 'created_at') else "Recent"
        
        # Sanitize content before sending to AI
        prompt_clean = sanitize_journal_content_for_ai(entry.prompt, 50)
        answer_clean = sanitize_journal_content_for_ai(entry.answer, 100)
        
        if prompt_clean and answer_clean:
            formatted_entries_list.append(
                f"- On {date_str}, topic: '{prompt_clean}'. Response: '{answer_clean}'"
            )
    
    if not formatted_entries_list:
        return "No recent journal activity to reference."
    
    return (
        "Here's a brief overview of recent journal activity for context:\n"
        + "\n".join(formatted_entries_list[:5])  # Limit to 5 entries max
        + "\n\nNow, how can I help you today?"
    )

def call_gemini_api(model, contents, retries=2):
    """Enhanced Gemini API call with retry logic and better error handling."""
    for attempt in range(retries + 1):
        try:
            response = model.generate_content(
                contents,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 1024,
                    "top_p": 0.8
                }
            )
            
            # Check for safety blocks
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason'):
                    return "I can't respond to that request. Let's try discussing something else."
            
            # Check for content
            if response.candidates and response.candidates[0].content.parts:
                response_text = response.text.strip()
                if response_text:
                    return response_text
                else:
                    return "I'm having trouble forming a response. Could you try rephrasing?"
            else:
                if attempt < retries:
                    continue
                return "I'm currently unable to generate a response. Please try again."
                
        except Exception as e:
            current_app.logger.warning(f"Gemini API attempt {attempt + 1} failed: {str(e)}")
            
            # Handle specific error types
            error_str = str(e).lower()
            if "quota" in error_str or "limit" in error_str:
                return "I'm experiencing high demand right now. Please try again in a few minutes."
            elif "safety" in error_str:
                return "I can't respond to that due to safety guidelines. Let's discuss something else."
            elif attempt == retries:
                return "I'm having technical difficulties. Please try again later."
    
    return "Sorry, I encountered an issue and couldn't process your message."

def generate_conversation_title(chat_data):
    """Generate a meaningful title from conversation data."""
    if not chat_data:
        return "New Chat"
    
    # Find first substantial user message
    for message in chat_data:
        if message.get("role") == "user" and message.get("parts"):
            first_message = message["parts"][0] if message["parts"] else ""
            if first_message and len(first_message.strip()) > 3:
                # Clean and truncate for title
                title = first_message.strip()[:40]
                if len(first_message) > 40:
                    title += "..."
                return title
    
    return "Chat Session"

def get_journal_context_for_new_chat():
    """Get journal context for new conversations with better error handling."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=JOURNAL_CONTEXT_DAYS)
        
        recent_entries = Journal.query.filter(
            Journal.user_id == current_user.id,
            Journal.created_at >= cutoff_date,
            Journal.deleted_at.is_(None),
            Journal.answer.isnot(None),
            Journal.answer != ''
        ).order_by(Journal.created_at.desc()).limit(MAX_JOURNAL_ENTRIES_FOR_CONTEXT).all()
        
        return format_entries_for_initial_context(recent_entries)
        
    except Exception as e:
        current_app.logger.warning(f"Failed to get journal context: {e}")
        return ""

@chat_bp.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations with pagination and better error handling."""
    try:
        # Add pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:
            per_page = 20
        
        # Query with better filtering and pagination
        pagination = Conversation.query.filter(
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None)
        ).order_by(Conversation.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = []
        for conv in pagination.items:
            try:
                chat_data = conv.get_chat_data()
                preview_title = generate_conversation_title(chat_data)
                
                # Get last message info
                last_message_preview = ""
                if chat_data:
                    # Get last AI response for preview
                    for message in reversed(chat_data):
                        if message.get("role") == "model" and message.get("parts"):
                            last_message = message["parts"][0] if message["parts"] else ""
                            if last_message:
                                last_message_preview = last_message[:60]
                                if len(last_message) > 60:
                                    last_message_preview += "..."
                                break
                
                result.append({
                    "id": conv.id,
                    "title": preview_title,
                    "last_message_preview": last_message_preview,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                    "message_count": len(chat_data) if chat_data else 0
                })
                
            except Exception as e:
                current_app.logger.warning(f"Error processing conversation {conv.id}: {e}")
                # Skip problematic conversations rather than failing entirely
                continue
        
        return jsonify({
            "conversations": result,
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
        current_app.logger.error(f"Error retrieving conversations: {str(e)}")
        return jsonify({"error": "Failed to retrieve conversations"}), 500

@chat_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
@login_required
def get_single_conversation_history(conversation_id):
    """Get the full chat history for a specific conversation."""
    try:
        # Validate conversation_id
        if conversation_id <= 0:
            return jsonify({"error": "Invalid conversation ID"}), 400
        
        conversation = Conversation.query.filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None)
        ).first()
        
        if not conversation:
            return jsonify({"error": "Conversation not found or access denied"}), 404
        
        chat_history = conversation.get_chat_data()
        
        # Clean history for frontend (remove any context messages)
        cleaned_history = []
        for message in chat_history:
            if message.get("role") == "user":
                # Only include the actual user message, not context
                parts = message.get("parts", [])
                if parts:
                    # Take the last part which should be the actual user message
                    user_message = parts[-1] if len(parts) > 1 else parts[0]
                    cleaned_history.append({
                        "role": "user",
                        "parts": [user_message]
                    })
            else:
                cleaned_history.append(message)
        
        return jsonify({
            "conversation_id": conversation.id,
            "title": generate_conversation_title(chat_history),
            "history": cleaned_history,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "message_count": len(cleaned_history)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving conversation history for ID {conversation_id}: {str(e)}")
        return jsonify({"error": "Failed to retrieve conversation history"}), 500

@chat_bp.route('/message', methods=['POST'])
@login_required
def post_message():
    """Enhanced message processing with better validation and error handling."""
    try:
        # Validate input
        validated_data, error = validate_message_input(request.get_json())
        if error:
            return jsonify({"error": error}), 400
        
        user_message_text = validated_data["message"]
        conversation_id = validated_data["conversation_id"]
        
        # Check API configuration
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            current_app.logger.error("GEMINI_API_KEY not configured")
            return jsonify({"error": "Chat service temporarily unavailable"}), 503
        
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            current_app.logger.error(f"Gemini configuration failed: {e}")
            return jsonify({"error": "Chat service initialization failed"}), 503
        
        system_instruction = (
            "You are Kai, a compassionate and insightful journaling companion. Help users explore "
            "their thoughts and feelings with empathy and wisdom. Ask thoughtful questions, offer "
            "gentle perspectives, and help users connect insights from their experiences. "
            "Keep responses conversational, supportive, and under 200 words unless more detail is specifically requested. "
            "If referencing their journal entries, do so thoughtfully and with respect for their privacy. "
            "Focus on encouraging self-reflection and personal growth."
        )
        
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=system_instruction
            )
        except Exception as e:
            current_app.logger.error(f"Failed to create Gemini model: {e}")
            return jsonify({"error": "Chat service initialization failed"}), 503
        
        # Handle conversation management
        conversation_object = None
        is_new_chat = False
        journal_context = ""
        
        if conversation_id:
            conversation_object = Conversation.query.filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
                Conversation.deleted_at.is_(None)
            ).first()
            
            if not conversation_object:
                return jsonify({"error": "Conversation not found or access denied"}), 404
            
            chat_history = conversation_object.get_chat_data()
        else:
            # Create new conversation
            is_new_chat = True
            conversation_object = Conversation(user_id=current_user.id)
            db.session.add(conversation_object)
            db.session.flush()  # Get ID without committing
            
            chat_history = []
            
            # Add journal context for new conversations
            journal_context = get_journal_context_for_new_chat()
        
        # Prepare AI input
        contents_for_ai = list(chat_history)
        
        # Add current message (with context if new chat)
        current_message_parts = []
        if is_new_chat and journal_context:
            current_message_parts.append(journal_context)
        current_message_parts.append(user_message_text)
        
        contents_for_ai.append({"role": "user", "parts": current_message_parts})
        
        # Get AI response
        ai_response_text = call_gemini_api(model, contents_for_ai)
        
        # Update chat history for database
        chat_history.append({"role": "user", "parts": [user_message_text]})
        chat_history.append({"role": "model", "parts": [ai_response_text]})
        
        # Save to database
        conversation_object.set_chat_data(chat_history)
        db.session.commit()
        
        # Log successful interaction (without sensitive data)
        current_app.logger.info(
            f"Chat message processed for user {current_user.id}, "
            f"conversation {conversation_object.id}, new_chat: {is_new_chat}"
        )
        
        return jsonify({
            "ai_message": ai_response_text,
            "conversation_id": conversation_object.id,
            "user_message_echo": user_message_text,
            "is_new_conversation": is_new_chat
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Chat message processing failed: {str(e)}")
        return jsonify({
            "error": "Failed to process message. Please try again."
        }), 500

@chat_bp.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete a conversation (soft delete)."""
    try:
        # Validate conversation_id
        if conversation_id <= 0:
            return jsonify({"error": "Invalid conversation ID"}), 400
        
        # Fetch conversation, including those already soft-deleted to prevent errors if called twice
        conversation = Conversation.query.filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            return jsonify({"error": "Conversation not found or access denied"}), 404

        # Check if already deleted
        if hasattr(conversation, 'deleted_at') and conversation.deleted_at is not None:
            return jsonify({"message": "Conversation was already deleted"}), 200  # Idempotency
        
        # Soft delete
        if hasattr(conversation, 'deleted_at'):
            conversation.deleted_at = datetime.utcnow()
            action_taken = "soft deleted"
        else:
            # Fallback to hard delete if no deleted_at attribute (shouldn't happen with Base model)
            db.session.delete(conversation)
            action_taken = "hard deleted"
            
        db.session.commit()
        
        current_app.logger.info(
            f"Conversation {conversation_id} {action_taken} by user {current_user.id}"
        )
        
        return jsonify({"message": f"Conversation {action_taken} successfully"}), 200
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        return jsonify({"error": "Failed to delete conversation"}), 500

@chat_bp.route('/conversations/<int:conversation_id>/title', methods=['PUT'])
@login_required
def update_conversation_title(conversation_id):
    """Update conversation title (custom titles)."""
    try:
        # Validate conversation_id
        if conversation_id <= 0:
            return jsonify({"error": "Invalid conversation ID"}), 400
        
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({"error": "Title is required"}), 400
        
        new_title = data['title'].strip()
        if not new_title:
            return jsonify({"error": "Title cannot be empty"}), 400
        
        if len(new_title) > 100:
            return jsonify({"error": "Title too long (maximum 100 characters)"}), 400
        
        # Sanitize title
        clean_title = bleach.clean(new_title, tags=[], strip=True)
        
        conversation = Conversation.query.filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None)
        ).first()
        
        if not conversation:
            return jsonify({"error": "Conversation not found or access denied"}), 404
        
        conversation.title = clean_title
        db.session.commit()
        
        return jsonify({
            "message": "Title update feature coming soon",
            "requested_title": clean_title
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating conversation title: {str(e)}")
        return jsonify({"error": "Failed to update conversation title"}), 500
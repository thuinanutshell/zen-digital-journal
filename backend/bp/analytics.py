from backend.models import db, Journal
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import os
import google.generativeai as genai
import json
import re
import hashlib
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

def remove_sensitive_info(text):
    """Remove potentially sensitive information from text."""
    if not text:
        return text
    
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Remove phone numbers (basic patterns)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    
    # Remove potential SSN patterns
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    
    # Remove credit card-like number patterns
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', text)
    
    # Remove addresses (basic pattern for street numbers and names)
    text = re.sub(r'\b\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)\b', '[ADDRESS]', text, flags=re.IGNORECASE)
    
    return text.strip()

def sanitize_entries_for_ai(entries, max_entries=31):
    """Enhanced sanitization with better privacy protection."""
    limited_entries = entries[:max_entries]
    formatted_entries = []
    
    for entry in limited_entries:
        # More conservative text limiting for privacy
        prompt = entry.prompt[:50] if entry.prompt else ""
        answer = entry.answer[:200] if entry.answer else ""
        
        # Remove potentially sensitive information
        prompt = remove_sensitive_info(prompt)
        answer = remove_sensitive_info(answer)
        
        # Use relative dates for additional privacy (month-day only)
        date = entry.created_at.strftime("%m-%d") if hasattr(entry, 'created_at') else "Unknown"
        
        # Add modality info for context
        modality = getattr(entry, 'modality', 'text')
        
        formatted_entries.append(
            f"Date: {date}, Modality: {modality}, Topic: {prompt}, Content: {answer}"
        )
    
    return "\n\n".join(formatted_entries)

def call_ai_service(sanitized_entries, retries=2):
    """Enhanced AI service call with retries and better error handling."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        raise ValueError(f"Failed to initialize AI client: {str(e)}")
    
    prompt = (
        "You are a supportive journal analysis assistant. Analyze these journal entries and provide "
        "encouraging, constructive insights. Focus on positive patterns and growth opportunities.\n\n"
        "Provide your response in this exact JSON format (no markdown code blocks):\n"
        "{\n"
        '  "patterns": ["pattern1", "pattern2", "pattern3"],\n'
        '  "insights": ["insight1", "insight2"],\n'
        '  "suggested_prompts": ["prompt1", "prompt2", "prompt3"]\n'
        "}\n\n"
        "Guidelines:\n"
        "- Keep responses encouraging and constructive\n"
        "- Focus on personal growth and positive developments\n"
        "- Suggest thoughtful, open-ended prompts for future journaling\n"
        "- Be specific but not overly personal\n\n"
        f"Journal entries to analyze:\n{sanitized_entries}"
    )
    
    for attempt in range(retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                generation_config={
                    "temperature": 0.3,  # Lower temperature for more consistent JSON
                    "max_output_tokens": 1024,
                    "top_p": 0.8
                }
            )
            
            if not response.text:
                raise ValueError("Empty response from AI service")
            
            # Clean response text (remove any markdown formatting)
            clean_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            elif clean_text.startswith('```'):
                clean_text = clean_text[3:]
            
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            # Parse JSON
            result = json.loads(clean_text)
            
            # Validate and sanitize response structure
            validated_result = validate_ai_response(result)
            
            return validated_result
            
        except json.JSONDecodeError as e:
            current_app.logger.warning(f"JSON parsing failed on attempt {attempt + 1}: {e}")
            current_app.logger.debug(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            
            if attempt == retries:
                # Return fallback response
                return get_fallback_analysis()
                
        except Exception as e:
            current_app.logger.error(f"AI service error on attempt {attempt + 1}: {e}")
            
            if attempt == retries:
                if "quota" in str(e).lower() or "limit" in str(e).lower():
                    raise ValueError("AI service quota exceeded. Please try again later.")
                else:
                    raise ValueError(f"AI service temporarily unavailable: {str(e)}")
    
    return get_fallback_analysis()

def validate_ai_response(result):
    """Validate and sanitize AI response structure."""
    validated = {
        "patterns": [],
        "insights": [],
        "suggested_prompts": []
    }
    
    # Validate patterns
    if "patterns" in result and isinstance(result["patterns"], list):
        validated["patterns"] = [str(p)[:200] for p in result["patterns"][:5] if p]
    
    # Validate insights
    if "insights" in result and isinstance(result["insights"], list):
        validated["insights"] = [str(i)[:300] for i in result["insights"][:3] if i]
    
    # Validate suggested prompts
    if "suggested_prompts" in result and isinstance(result["suggested_prompts"], list):
        validated["suggested_prompts"] = [str(p)[:150] for p in result["suggested_prompts"][:5] if p]
    
    # Ensure minimum content
    if not validated["patterns"]:
        validated["patterns"] = ["Continue journaling to identify patterns in your thoughts and experiences"]
    
    if not validated["insights"]:
        validated["insights"] = ["Your journaling practice shows commitment to self-reflection and growth"]
    
    if not validated["suggested_prompts"]:
        validated["suggested_prompts"] = [
            "What did I learn about myself today?",
            "What am I most grateful for right now?",
            "How have I grown or changed recently?"
        ]
    
    return validated

def get_fallback_analysis():
    """Return a helpful fallback analysis when AI service fails."""
    return {
        "patterns": [
            "Your consistent journaling shows dedication to self-reflection",
            "You're actively engaging with your thoughts and experiences",
            "Regular writing practice indicates commitment to personal growth"
        ],
        "insights": [
            "Maintaining a journal demonstrates self-awareness and mindfulness",
            "Your writing practice creates space for processing daily experiences"
        ],
        "suggested_prompts": [
            "What did I accomplish today that I'm proud of?",
            "What challenge helped me learn something new about myself?",
            "What am I looking forward to in the coming days?",
            "How did I show kindness to myself or others today?",
            "What would I like to focus on improving tomorrow?"
        ]
    }

def generate_cache_key(user_id, days, max_entries, entry_ids):
    """Generate cache key based on parameters and actual entries."""
    # Create a deterministic hash of the parameters and entry content
    content = f"{user_id}_{days}_{max_entries}_{hash(tuple(sorted(entry_ids)))}"
    return f"analytics_{hashlib.md5(content.encode()).hexdigest()}"

@analytics_bp.route('/analyze', methods=['GET'])
@login_required
def analyze_entries():
    """Analyze user's journal entries using AI with enhanced error handling and caching."""
    try:
        # Validate and sanitize parameters
        days = request.args.get('days', default=30, type=int)
        max_entries = request.args.get('max_entries', default=25, type=int)
        force_refresh = request.args.get('force_refresh', default=False, type=bool)
        
        # Parameter validation
        if days < 1 or days > 365:
            return jsonify({
                "error": "Days parameter must be between 1 and 365"
            }), 400
        
        if max_entries < 1 or max_entries > 50:
            return jsonify({
                "error": "Max entries parameter must be between 1 and 50"
            }), 400
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get entries with comprehensive filtering
        entries = Journal.query.filter(
            Journal.user_id == current_user.id,
            Journal.deleted_at.is_(None),  # Exclude soft-deleted entries
            Journal.created_at >= cutoff_date,
            Journal.answer.isnot(None),  # Only entries with content
            Journal.answer != ''
        ).order_by(Journal.created_at.desc()).limit(max_entries).all()
        
        # Check if we have enough data
        if not entries:
            return jsonify({
                "message": "No journal entries found for analysis",
                "results": {
                    "patterns": ["No entries available for analysis"],
                    "insights": ["Start journaling to unlock personalized insights"],
                    "suggested_prompts": [
                        "What happened today that I want to remember?",
                        "How am I feeling right now and why?",
                        "What is one thing I'm grateful for today?"
                    ]
                },
                "entries_analyzed": 0,
                "date_range": {
                    "from": cutoff_date.strftime("%Y-%m-%d"),
                    "to": datetime.utcnow().strftime("%Y-%m-%d"),
                    "days": days
                }
            }), 200
        
        # Check for minimum entries for meaningful analysis
        if len(entries) < 3:
            return jsonify({
                "message": "Need more entries for comprehensive analysis",
                "results": {
                    "patterns": ["Continue journaling to identify meaningful patterns"],
                    "insights": [
                        "You're building a valuable habit of self-reflection",
                        "Each entry contributes to your personal growth journey"
                    ],
                    "suggested_prompts": [
                        "What emotions did I experience today?",
                        "What went well today and what could be improved?",
                        "What would I like to focus on tomorrow?"
                    ]
                },
                "entries_analyzed": len(entries),
                "date_range": {
                    "from": cutoff_date.strftime("%Y-%m-%d"),
                    "to": datetime.utcnow().strftime("%Y-%m-%d"),
                    "days": days
                }
            }), 200
        
        # Generate cache key and check cache (if not forcing refresh)
        cache_key = generate_cache_key(current_user.id, days, max_entries, [e.id for e in entries])
        
        # in production, we will use Redis or similar for caching
        # For now, we'll skip caching but keep the structure
        cached_result = None
        if not force_refresh:
            # cached_result = cache.get(cache_key)
            pass
        
        if cached_result:
            current_app.logger.info(f"Returning cached analytics for user {current_user.id}")
            return jsonify(cached_result), 200
        
        # Sanitize entries for AI processing
        sanitized_entries = sanitize_entries_for_ai(entries, max_entries)
        
        # Call AI service with enhanced error handling
        try:
            ai_result = call_ai_service(sanitized_entries)
        except ValueError as ve:
            # Handle specific AI service errors
            if "quota" in str(ve).lower() or "limit" in str(ve).lower():
                return jsonify({
                    "error": "Analysis service temporarily unavailable due to high demand. Please try again later."
                }), 503
            else:
                # Return fallback analysis for other AI errors
                ai_result = get_fallback_analysis()
                current_app.logger.warning(f"Using fallback analysis due to AI error: {ve}")
        
        # Prepare response
        response_data = {
            "message": "Analysis completed successfully",
            "results": ai_result,
            "entries_analyzed": len(entries),
            "date_range": {
                "from": cutoff_date.strftime("%Y-%m-%d"),
                "to": datetime.utcnow().strftime("%Y-%m-%d"),
                "days": days
            },
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the result (implement with your preferred caching solution)
        # cache.set(cache_key, response_data, timeout=3600)  # Cache for 1 hour
        
        # Log successful analysis (without sensitive data)
        current_app.logger.info(
            f"Analytics completed for user {current_user.id}: "
            f"{len(entries)} entries analyzed over {days} days"
        )
        
        return jsonify(response_data), 200
    
    except ValueError as ve:
        current_app.logger.error(f"Analytics configuration error: {str(ve)}")
        return jsonify({
            "error": "Analytics service configuration error. Please contact support."
        }), 503
    
    except Exception as e:
        current_app.logger.error(f"Unexpected analytics error: {str(e)}")
        return jsonify({
            "error": "Analysis failed due to an unexpected error. Please try again later."
        }), 500

@analytics_bp.route('/mood-trends', methods=['GET'])
@login_required
def get_mood_trends():
    """Get basic mood and activity trends from journal entries."""
    try:
        days = request.args.get('days', default=30, type=int)
        
        if days < 1 or days > 365:
            return jsonify({"error": "Days parameter must be between 1 and 365"}), 400
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get entries grouped by date
        entries = Journal.query.filter(
            Journal.user_id == current_user.id,
            Journal.deleted_at.is_(None),
            Journal.created_at >= cutoff_date
        ).order_by(Journal.created_at.desc()).all()
        
        if not entries:
            return jsonify({
                "message": "No entries found for trend analysis",
                "trends": {
                    "total_entries": 0,
                    "entries_by_modality": {},
                    "daily_activity": [],
                    "active_days": 0
                }
            }), 200
        
        # Calculate trends
        modality_counts = {}
        daily_counts = {}
        
        for entry in entries:
            # Count by modality
            modality = getattr(entry, 'modality', 'text')
            modality_counts[modality] = modality_counts.get(modality, 0) + 1
            
            # Count by day
            day_key = entry.created_at.strftime("%Y-%m-%d")
            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
        
        # Prepare daily activity data
        daily_activity = []
        for day, count in sorted(daily_counts.items()):
            daily_activity.append({
                "date": day,
                "entries": count
            })
        
        return jsonify({
            "message": "Trend analysis completed",
            "trends": {
                "total_entries": len(entries),
                "entries_by_modality": modality_counts,
                "daily_activity": daily_activity,
                "active_days": len(daily_counts),
                "date_range": {
                    "from": cutoff_date.strftime("%Y-%m-%d"),
                    "to": datetime.utcnow().strftime("%Y-%m-%d"),
                    "days": days
                }
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Trend analysis error: {str(e)}")
        return jsonify({"error": "Trend analysis failed"}), 500

@analytics_bp.route('/summary', methods=['GET'])
@login_required
def get_analytics_summary():
    """Get a quick summary of user's journaling analytics without AI processing."""
    try:
        # Get basic stats
        total_entries = Journal.query.filter_by(user_id=current_user.id) \
                                   .filter(Journal.deleted_at.is_(None)) \
                                   .count()
        
        if total_entries == 0:
            return jsonify({
                "message": "No entries found",
                "summary": {
                    "total_entries": 0,
                    "current_streak": current_user.current_streak,
                    "longest_streak": current_user.longest_streak,
                    "entries_this_month": 0,
                    "most_active_day": None
                }
            }), 200
        
        # Get entries from last 30 days
        last_month = datetime.utcnow() - timedelta(days=30)
        recent_entries = Journal.query.filter(
            Journal.user_id == current_user.id,
            Journal.deleted_at.is_(None),
            Journal.created_at >= last_month
        ).all()
        
        # Find most active day of week
        day_counts = {}
        for entry in recent_entries:
            day_name = entry.created_at.strftime("%A")
            day_counts[day_name] = day_counts.get(day_name, 0) + 1
        
        most_active_day = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else None
        
        return jsonify({
            "message": "Analytics summary generated",
            "summary": {
                "total_entries": total_entries,
                "current_streak": current_user.current_streak,
                "longest_streak": current_user.longest_streak,
                "entries_this_month": len(recent_entries),
                "most_active_day": most_active_day,
                "entries_by_day": day_counts
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Analytics summary error: {str(e)}")
        return jsonify({"error": "Failed to generate analytics summary"}), 500
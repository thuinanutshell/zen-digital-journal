from flask import jsonify

def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "Bad request",
            "message": "The request could not be understood by the server"
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication required"
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "error": "Forbidden",
            "message": "You don't have permission to access this resource"
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Not found",
            "message": "The requested resource was not found"
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "error": "Method not allowed",
            "message": "The method is not allowed for this endpoint"
        }), 405
    
    @app.errorhandler(413)
    def payload_too_large(error):
        return jsonify({
            "error": "Payload too large",
            "message": "File size exceeds the maximum allowed limit"
        }), 413
    
    @app.errorhandler(429)
    def ratelimit_handler(error):
        return jsonify({
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": error.retry_after
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        # Log the error
        app.logger.error(f'Server Error: {error}')
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        return jsonify({
            "error": "Service unavailable",
            "message": "The service is temporarily unavailable"
        }), 503
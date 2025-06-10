"""
User Mode Management API Endpoints
API endpoints dla zarządzania trybami użytkownika w Web UI
"""

from flask import Blueprint, request, jsonify, session
from typing import Dict, Any, Optional
import logging

# Import our systems
from mode_integrator import user_integrator
from auth_system import auth_manager, Permission, UserRole, UserMode
from user_modes import user_mode_manager

logger = logging.getLogger(__name__)

# Create Blueprint for user mode management
user_mode_bp = Blueprint('user_mode', __name__, url_prefix='/api/user_mode')

def get_current_session_id() -> Optional[str]:
    """Pobiera ID sesji z Flask session."""
    return session.get('session_id')

def require_authentication(func):
    """Decorator wymagający uwierzytelnienia."""
    def wrapper(*args, **kwargs):
        session_id = get_current_session_id()
        if not session_id:
            return jsonify({"error": "Authentication required"}), 401
        
        user = auth_manager.validate_session(session_id)
        if not user:
            return jsonify({"error": "Invalid session"}), 401
        
        return func(*args, **kwargs)
    
    wrapper.__name__ = func.__name__
    return wrapper

def require_permission(permission: Permission):
    """Decorator wymagający określonych uprawnień."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            session_id = get_current_session_id()
            if not session_id or not auth_manager.has_permission(session_id, permission):
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        return wrapper
    
    return decorator

@user_mode_bp.route('/login', methods=['POST'])
def login():
    """Endpoint logowania."""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        # Get client info
        ip_address = request.remote_addr or ""
        user_agent = request.headers.get('User-Agent', "")
        
        # Authenticate using integrator
        success, message = user_integrator.authenticate_and_setup(
            username, password, ip_address, user_agent
        )
        
        if success:
            # Store session ID in Flask session
            session['session_id'] = user_integrator.current_session_id
            
            user_info = user_integrator.get_user_info()
            return jsonify({
                "success": True,
                "message": message,
                "user": user_info
            })
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/logout', methods=['POST'])
@require_authentication
def logout():
    """Endpoint wylogowania."""
    try:
        success = user_integrator.logout()
        
        if success:
            session.pop('session_id', None)
            return jsonify({"success": True, "message": "Logged out successfully"})
        else:
            return jsonify({"error": "Logout failed"}), 500
            
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/status', methods=['GET'])
def status():
    """Endpoint sprawdzania statusu uwierzytelnienia."""
    try:
        session_id = get_current_session_id()
        
        if session_id:
            user = auth_manager.validate_session(session_id)
            if user:
                user_info = user_integrator.get_user_info()
                return jsonify({
                    "authenticated": True,
                    "user": user_info
                })
        
        return jsonify({"authenticated": False})
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/info', methods=['GET'])
@require_authentication
def get_user_info():
    """Endpoint zwracający informacje o użytkowniku."""
    try:
        user_info = user_integrator.get_user_info()
        mode_info = user_integrator.get_mode_info()
        available_features = user_integrator.get_available_features()
        usage_stats = user_integrator.get_usage_stats()
        
        return jsonify({
            "user": user_info,
            "mode": mode_info,
            "features": available_features,
            "stats": usage_stats
        })
        
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/modes', methods=['GET'])
@require_authentication
def get_available_modes():
    """Endpoint zwracający dostępne tryby dla użytkownika."""
    try:
        all_modes = user_mode_manager.get_available_modes()
        current_mode = user_mode_manager.get_current_mode()
        
        # Get user to determine accessible modes
        session_id = get_current_session_id()
        user = auth_manager.validate_session(session_id)
        
        if not user:
            return jsonify({"error": "Invalid session"}), 401
        
        # Determine accessible modes based on user role
        accessible_modes = {}
        
        for mode, config in all_modes.items():
            # Check if user can access this mode
            can_access = False
            
            if mode == UserMode.POOR_MAN:
                can_access = True  # Everyone can access Poor Man mode
            elif mode == UserMode.PAID_USER:
                can_access = user.role in [UserRole.PREMIUM, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            elif mode == UserMode.ENTERPRISE:
                can_access = user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            
            accessible_modes[mode.value] = {
                "name": config.name,
                "display_name": config.display_name,
                "description": config.description,
                "features": config.features,
                "pricing": config.pricing,
                "can_access": can_access,
                "is_current": mode == current_mode
            }
        
        return jsonify({
            "modes": accessible_modes,
            "current_mode": current_mode.value
        })
        
    except Exception as e:
        logger.error(f"Get modes error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/switch_mode', methods=['POST'])
@require_authentication
def switch_mode():
    """Endpoint przełączania trybu użytkownika."""
    try:
        data = request.get_json()
        new_mode_str = data.get('mode')
        
        if not new_mode_str:
            return jsonify({"error": "Mode parameter required"}), 400
        
        try:
            new_mode = UserMode(new_mode_str)
        except ValueError:
            return jsonify({"error": "Invalid mode"}), 400
        
        success, message = user_integrator.switch_mode(new_mode)
        
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "new_mode": new_mode.value
            })
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 403
            
    except Exception as e:
        logger.error(f"Switch mode error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/test_tts', methods=['POST'])
@require_authentication
def test_tts():
    """Endpoint testowania TTS."""
    try:
        data = request.get_json()
        text = data.get('text', 'Hello, this is a TTS test.')
        
        # Check TTS permission
        session_id = get_current_session_id()
        if not auth_manager.has_permission(session_id, Permission.USE_TTS):
            return jsonify({"error": "TTS permission required"}), 403
        
        success = user_integrator.speak_text(text)
        
        if success:
            return jsonify({
                "success": True,
                "message": "TTS test completed"
            })
        else:
            return jsonify({
                "success": False,
                "error": "TTS test failed"
            }), 500
            
    except Exception as e:
        logger.error(f"TTS test error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/users', methods=['GET'])
@require_permission(Permission.USER_MANAGEMENT)
def list_users():
    """Endpoint listowania użytkowników (tylko dla adminów)."""
    try:
        session_id = get_current_session_id()
        users = auth_manager.get_all_users(session_id)
        
        if users is None:
            return jsonify({"error": "Access denied"}), 403
        
        return jsonify({"users": users})
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/users/<user_id>/role', methods=['PUT'])
@require_permission(Permission.USER_MANAGEMENT)
def update_user_role(user_id: str):
    """Endpoint aktualizacji roli użytkownika (tylko dla adminów)."""
    try:
        data = request.get_json()
        new_role_str = data.get('role')
        
        if not new_role_str:
            return jsonify({"error": "Role parameter required"}), 400
        
        try:
            new_role = UserRole(new_role_str)
        except ValueError:
            return jsonify({"error": "Invalid role"}), 400
        
        session_id = get_current_session_id()
        success = auth_manager.update_user_role(user_id, new_role, session_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"User role updated to {new_role.value}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to update user role"
            }), 500
            
    except Exception as e:
        logger.error(f"Update user role error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_mode_bp.route('/create_user', methods=['POST'])
@require_permission(Permission.USER_MANAGEMENT)
def create_user():
    """Endpoint tworzenia nowego użytkownika (tylko dla adminów)."""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role_str = data.get('role', 'user')
        
        if not all([username, email, password]):
            return jsonify({"error": "Username, email, and password required"}), 400
        
        try:
            role = UserRole(role_str)
        except ValueError:
            return jsonify({"error": "Invalid role"}), 400
        
        user_id = auth_manager.create_user(username, email, password, role)
        
        if user_id:
            return jsonify({
                "success": True,
                "message": "User created successfully",
                "user_id": user_id
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to create user"
            }), 400
            
    except Exception as e:
        logger.error(f"Create user error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Error handlers
@user_mode_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@user_mode_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

@user_mode_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

"""
Firebase Authentication API Routes

Purpose: Handle Firebase authentication and sync with MongoDB
Endpoints:
- POST /api/auth/register - Register new user with role selection
- POST /api/auth/login - Login user and sync with MongoDB
- GET /api/auth/user/:firebase_uid - Get user by Firebase UID
- PUT /api/auth/user/:firebase_uid/role - Update user role
"""

from flask import Blueprint, request, jsonify
import logging

from services.firebase_auth_service import FirebaseAuthService
from db.models import UserRole

logger = logging.getLogger(__name__)

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Initialize service
firebase_auth_service = FirebaseAuthService()


@auth_bp.route('/register', methods=['POST'])
def register_user():
    """
    Register a new user with Firebase and sync to MongoDB
    
    Request Body:
    {
        "firebase_uid": "string",
        "email": "string",
        "full_name": "string",
        "role": "hr" | "employee",
        "company": "string" (optional, for HR),
        "phone": "string" (optional)
    }
    
    Response:
    {
        "success": true,
        "user": {...},
        "message": "User registered successfully"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['firebase_uid', 'email', 'full_name', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate role
        role = data['role'].lower()
        if role not in [UserRole.HR, UserRole.EMPLOYEE]:
            return jsonify({
                'success': False,
                'error': 'Invalid role. Must be "hr" or "employee"'
            }), 400
        
        # Register user
        user = firebase_auth_service.register_user_with_role(
            firebase_uid=data['firebase_uid'],
            email=data['email'],
            full_name=data['full_name'],
            role=role,
            company=data.get('company'),
            phone=data.get('phone')
        )
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Failed to register user'
            }), 500
        
        return jsonify({
            'success': True,
            'user': user,
            'message': f'User registered successfully as {role}'
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login_user():
    """
    Login user with Firebase and sync to MongoDB
    
    Request Body:
    {
        "firebase_uid": "string",
        "email": "string"
    }
    
    Response:
    {
        "success": true,
        "user": {...},
        "message": "Login successful"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'firebase_uid' not in data or 'email' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing firebase_uid or email'
            }), 400
        
        # Login user
        user = firebase_auth_service.login_user(
            firebase_uid=data['firebase_uid'],
            email=data['email']
        )
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Login failed'
            }), 401
        
        return jsonify({
            'success': True,
            'user': user,
            'message': 'Login successful'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/user/<firebase_uid>', methods=['GET'])
def get_user(firebase_uid):
    """
    Get user by Firebase UID
    
    Response:
    {
        "success": true,
        "user": {...}
    }
    """
    try:
        user = firebase_auth_service.get_user_by_firebase_uid(firebase_uid)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Get user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/user/<firebase_uid>/role', methods=['PUT'])
def update_user_role(firebase_uid):
    """
    Update user's role
    
    Request Body:
    {
        "role": "hr" | "employee"
    }
    
    Response:
    {
        "success": true,
        "message": "Role updated successfully"
    }
    """
    try:
        data = request.get_json()
        
        if 'role' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing role field'
            }), 400
        
        role = data['role'].lower()
        if role not in [UserRole.HR, UserRole.EMPLOYEE]:
            return jsonify({
                'success': False,
                'error': 'Invalid role. Must be "hr" or "employee"'
            }), 400
        
        success = firebase_auth_service.update_user_role(firebase_uid, role)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to update role'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'Role updated to {role}'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Update role error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/users/role/<role>', methods=['GET'])
def get_users_by_role(role):
    """
    Get all users with a specific role
    
    Response:
    {
        "success": true,
        "users": [...],
        "count": 5
    }
    """
    try:
        role = role.lower()
        if role not in [UserRole.HR, UserRole.EMPLOYEE, UserRole.ADMIN]:
            return jsonify({
                'success': False,
                'error': 'Invalid role'
            }), 400
        
        users = firebase_auth_service.get_users_by_role(role)
        
        return jsonify({
            'success': True,
            'users': users,
            'count': len(users)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Get users by role error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/user/<user_id>', methods=['DELETE'])
def delete_user_by_id(user_id):
    """
    Delete user from both MongoDB and Firebase Auth
    
    This endpoint will:
    1. Delete user from MongoDB
    2. Automatically delete user from Firebase Auth (if Firebase UID exists)
    3. Return detailed deletion status
    
    Response:
    {
        "success": true,
        "message": "User deleted from MongoDB and Firebase Auth",
        "mongodb_deleted": true,
        "firebase_deleted": true,
        "firebase_message": "Deleted from Firebase Auth",
        "firebase_uid": "firebase-abc123"
    }
    """
    try:
        result = firebase_auth_service.delete_user(user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
        
    except Exception as e:
        logger.error(f"❌ Delete user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'mongodb_deleted': False,
            'firebase_deleted': False
        }), 500


@auth_bp.route('/user/email/<email>', methods=['DELETE'])
def delete_user_by_email_route(email):
    """
    Delete user by email from both MongoDB and Firebase Auth
    
    Response:
    {
        "success": true,
        "message": "User deleted from MongoDB and Firebase Auth",
        "mongodb_deleted": true,
        "firebase_deleted": true,
        "firebase_message": "Deleted from Firebase Auth"
    }
    """
    try:
        result = firebase_auth_service.delete_user_by_email(email)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
        
    except Exception as e:
        logger.error(f"❌ Delete user by email error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'mongodb_deleted': False,
            'firebase_deleted': False
        }), 500


# Health check endpoint
@auth_bp.route('/health', methods=['GET'])
def health_check():
    """Check if authentication service is running"""
    return jsonify({
        'success': True,
        'service': 'Firebase Authentication',
        'status': 'running'
    }), 200

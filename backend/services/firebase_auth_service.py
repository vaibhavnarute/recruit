"""
Firebase Authentication Service

Purpose: Integrate Firebase authentication with MongoDB user management
Features:
- Sync Firebase users to MongoDB
- Role-based access (HR and Employee)
- Unified authentication flow
- Automatic Firebase Auth cleanup when deleting MongoDB users
"""

import logging
import os
from typing import Optional, Dict
from datetime import datetime

from repositories.user_repository import UserRepository
from db.models import UserRole

logger = logging.getLogger(__name__)

# Firebase Admin SDK (optional - for server-side user management)
try:
    import firebase_admin
    from firebase_admin import credentials, auth
    
    # Initialize Firebase Admin SDK if not already initialized
    if not firebase_admin._apps:
        # Try to initialize with service account
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase Admin SDK initialized")
        else:
            logger.warning("⚠️ Firebase Admin SDK not initialized (service account not found)")
            firebase_admin = None
except ImportError:
    logger.warning("⚠️ firebase-admin not installed. User deletion from Firebase Auth will be skipped.")
    firebase_admin = None
    auth = None


class FirebaseAuthService:
    """Service for Firebase authentication integration"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    def register_user_with_role(
        self,
        firebase_uid: str,
        email: str,
        full_name: str,
        role: str,
        company: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Register a new user from Firebase and sync to MongoDB
        
        Args:
            firebase_uid: Firebase user ID
            email: User email
            full_name: User's full name
            role: User role ('hr' or 'employee')
            company: Company name (for HR users)
            phone: Phone number
            
        Returns:
            User document if successful
        """
        try:
            # Validate role
            if role not in [UserRole.HR, UserRole.EMPLOYEE]:
                logger.error(f"Invalid role: {role}. Must be 'hr' or 'employee'")
                return None
            
            # Check if user already exists
            existing_user = self.user_repo.get_user_by_firebase_uid(firebase_uid)
            if existing_user:
                logger.info(f"User already registered: {email}")
                return existing_user
            
            # Check by email
            existing_email = self.user_repo.get_user_by_email(email)
            if existing_email:
                # Update with Firebase UID
                self.user_repo.collection.update_one(
                    {"email": email},
                    {"$set": {
                        "firebase_uid": firebase_uid,
                        "role": role,
                        "company": company,
                        "phone": phone,
                        "updated_at": datetime.utcnow()
                    }}
                )
                logger.info(f"Updated existing user with Firebase data: {email}")
                return self.user_repo.get_user_by_email(email)
            
            # Create new user
            user_doc = {
                "email": email,
                "firebase_uid": firebase_uid,
                "full_name": full_name,
                "role": role,
                "password": None,  # Firebase handles authentication
                "company": company if role == UserRole.HR else None,
                "phone": phone,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "last_login": datetime.utcnow()
            }
            
            result = self.user_repo.collection.insert_one(user_doc)
            logger.info(f"✅ New user registered: {email} as {role} (ID: {result.inserted_id})")
            
            return self.user_repo.get_user_by_id(str(result.inserted_id))
            
        except Exception as e:
            logger.error(f"❌ Failed to register user: {str(e)}")
            return None
    
    def login_user(self, firebase_uid: str, email: str) -> Optional[Dict]:
        """
        Handle user login from Firebase
        
        Args:
            firebase_uid: Firebase user ID
            email: User email
            
        Returns:
            User document with MongoDB data
        """
        try:
            # Get or create user in MongoDB
            user = self.user_repo.get_user_by_firebase_uid(firebase_uid)
            
            if not user:
                # User not in MongoDB yet, sync from Firebase
                logger.info(f"User not found in MongoDB, syncing: {email}")
                user_id = self.user_repo.sync_firebase_user(
                    firebase_uid=firebase_uid,
                    email=email,
                    full_name=email.split('@')[0],  # Use email prefix as name
                    role=UserRole.HR  # Default role
                )
                user = self.user_repo.get_user_by_id(user_id)
            
            # Update last login
            if user:
                self.user_repo.collection.update_one(
                    {"firebase_uid": firebase_uid},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                logger.info(f"✅ User logged in: {email}")
            
            return user
            
        except Exception as e:
            logger.error(f"❌ Login failed: {str(e)}")
            return None
    
    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[Dict]:
        """Get user by Firebase UID"""
        return self.user_repo.get_user_by_firebase_uid(firebase_uid)
    
    def update_user_role(self, firebase_uid: str, role: str) -> bool:
        """
        Update user's role
        
        Args:
            firebase_uid: Firebase user ID
            role: New role ('hr' or 'employee')
            
        Returns:
            True if successful
        """
        try:
            if role not in [UserRole.HR, UserRole.EMPLOYEE]:
                logger.error(f"Invalid role: {role}")
                return False
            
            user = self.user_repo.get_user_by_firebase_uid(firebase_uid)
            if not user:
                logger.error(f"User not found: {firebase_uid}")
                return False
            
            result = self.user_repo.collection.update_one(
                {"firebase_uid": firebase_uid},
                {"$set": {
                    "role": role,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            logger.info(f"✅ User role updated: {user['email']} -> {role}")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update role: {str(e)}")
            return False
    
    def get_users_by_role(self, role: str) -> list:
        """Get all users with a specific role"""
        return self.user_repo.get_all_users(role=role)
    
    def delete_user(self, user_id: str) -> Dict[str, any]:
        """
        Delete user from both MongoDB and Firebase Auth
        
        Args:
            user_id: MongoDB user ID
            
        Returns:
            Dict with success status and messages
        """
        try:
            # Delete from MongoDB (returns Firebase UID if exists)
            success, firebase_uid = self.user_repo.delete_user(user_id)
            
            if not success:
                return {
                    'success': False,
                    'message': 'User not found in MongoDB',
                    'mongodb_deleted': False,
                    'firebase_deleted': False
                }
            
            # Try to delete from Firebase Auth if Firebase UID exists
            firebase_deleted = False
            firebase_message = "No Firebase UID found"
            
            if firebase_uid and firebase_admin and auth:
                try:
                    auth.delete_user(firebase_uid)
                    firebase_deleted = True
                    firebase_message = "Deleted from Firebase Auth"
                    logger.info(f"✅ User deleted from Firebase Auth: {firebase_uid}")
                except Exception as fb_error:
                    firebase_message = f"Firebase deletion failed: {str(fb_error)}"
                    logger.warning(f"⚠️ Failed to delete from Firebase Auth: {str(fb_error)}")
            elif firebase_uid:
                firebase_message = "Firebase Admin SDK not available"
                logger.warning("⚠️ Firebase Admin SDK not initialized, skipping Firebase Auth deletion")
            
            return {
                'success': True,
                'message': 'User deleted from MongoDB' + (f' and Firebase Auth' if firebase_deleted else ''),
                'mongodb_deleted': True,
                'firebase_deleted': firebase_deleted,
                'firebase_message': firebase_message,
                'firebase_uid': firebase_uid
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to delete user: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'mongodb_deleted': False,
                'firebase_deleted': False
            }
    
    def delete_user_by_email(self, email: str) -> Dict[str, any]:
        """
        Delete user by email from both MongoDB and Firebase Auth
        
        Args:
            email: User email
            
        Returns:
            Dict with success status and messages
        """
        try:
            # Delete from MongoDB
            success, firebase_uid = self.user_repo.delete_user_by_email(email)
            
            if not success:
                return {
                    'success': False,
                    'message': 'User not found in MongoDB',
                    'mongodb_deleted': False,
                    'firebase_deleted': False
                }
            
            # Try to delete from Firebase Auth
            firebase_deleted = False
            firebase_message = "No Firebase UID found"
            
            if firebase_uid and firebase_admin and auth:
                try:
                    auth.delete_user(firebase_uid)
                    firebase_deleted = True
                    firebase_message = "Deleted from Firebase Auth"
                    logger.info(f"✅ User deleted from Firebase Auth: {firebase_uid}")
                except Exception as fb_error:
                    firebase_message = f"Firebase deletion failed: {str(fb_error)}"
                    logger.warning(f"⚠️ Failed to delete from Firebase Auth: {str(fb_error)}")
            elif firebase_uid:
                firebase_message = "Firebase Admin SDK not available"
            
            return {
                'success': True,
                'message': f'User {email} deleted from MongoDB' + (f' and Firebase Auth' if firebase_deleted else ''),
                'mongodb_deleted': True,
                'firebase_deleted': firebase_deleted,
                'firebase_message': firebase_message,
                'firebase_uid': firebase_uid
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to delete user: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'mongodb_deleted': False,
                'firebase_deleted': False
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    service = FirebaseAuthService()
    
    # Example: Register HR user
    hr_user = service.register_user_with_role(
        firebase_uid="firebase-test-123",
        email="hr@example.com",
        full_name="HR Manager",
        role=UserRole.HR,
        company="TechCorp",
        phone="+1234567890"
    )
    print(f"HR User: {hr_user}")
    
    # Example: Register Employee user
    employee_user = service.register_user_with_role(
        firebase_uid="firebase-test-456",
        email="employee@example.com",
        full_name="John Doe",
        role=UserRole.EMPLOYEE,
        phone="+0987654321"
    )
    print(f"Employee User: {employee_user}")

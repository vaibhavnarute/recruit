"""
User Repository - Handles all user-related database operations

Features:
- User registration and authentication
- Password hashing with bcrypt
- User profile management
- User search and retrieval
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
import bcrypt
from bson import ObjectId

from db.mongo_client import get_collection
from db.models import Collections, UserRole

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user data operations"""
    
    def __init__(self):
        self.collection = get_collection(Collections.USERS)
    
    def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: str = UserRole.HR,
        company: Optional[str] = None,
        firebase_uid: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new user account
        
        Args:
            email: User email (unique)
            password: Plain text password (will be hashed)
            full_name: User's full name
            role: User role (recruiter, admin, candidate)
            company: Company name
            
        Returns:
            User ID if successful, None otherwise
        """
        try:
            # Check if user already exists
            if self.collection.find_one({"email": email}):
                logger.warning(f"User with email {email} already exists")
                return None
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Create user document
            user_doc = {
                "email": email,
                "password": hashed_password,
                "full_name": full_name,
                "role": role,
                "company": company,
                "firebase_uid": firebase_uid,  # Store Firebase UID for integration
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "last_login": None
            }
            
            result = self.collection.insert_one(user_doc)
            logger.info(f"✅ User created: {email} (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to create user: {str(e)}")
            return None
    
    def authenticate(self, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with email and password
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User document if authenticated, None otherwise
        """
        try:
            user = self.collection.find_one({"email": email, "is_active": True})
            
            if not user:
                logger.warning(f"User not found: {email}")
                return None
            
            # Verify password
            if bcrypt.checkpw(password.encode('utf-8'), user['password']):
                # Update last login
                self.collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                
                # Remove password from returned document
                user.pop('password', None)
                user['_id'] = str(user['_id'])
                
                logger.info(f"✅ User authenticated: {email}")
                return user
            
            logger.warning(f"Invalid password for user: {email}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            user = self.collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user.pop('password', None)
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            logger.error(f"❌ Failed to get user: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            user = self.collection.find_one({"email": email})
            if user:
                user.pop('password', None)
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            logger.error(f"❌ Failed to get user: {str(e)}")
            return None
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user profile"""
        try:
            updates['updated_at'] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Failed to update user: {str(e)}")
            return False
    
    def get_all_users(self, role: Optional[str] = None) -> List[Dict]:
        """Get all users, optionally filtered by role"""
        try:
            query = {"role": role} if role else {}
            users = list(self.collection.find(query))
            
            for user in users:
                user.pop('password', None)
                user['_id'] = str(user['_id'])
            
            return users
        except Exception as e:
            logger.error(f"❌ Failed to get users: {str(e)}")
            return []
    
    def delete_user(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Delete user from MongoDB
        
        Args:
            user_id: MongoDB user ID
            
        Returns:
            Tuple of (success: bool, firebase_uid: Optional[str])
            Returns firebase_uid if user had one, so caller can delete from Firebase Auth
        """
        try:
            # Get user first to retrieve Firebase UID
            user = self.collection.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                logger.warning(f"User not found: {user_id}")
                return False, None
            
            firebase_uid = user.get('firebase_uid')
            
            # Delete from MongoDB
            result = self.collection.delete_one({"_id": ObjectId(user_id)})
            
            if result.deleted_count > 0:
                logger.info(f"✅ User deleted from MongoDB: {user.get('email')} (ID: {user_id})")
                return True, firebase_uid
            else:
                logger.warning(f"Failed to delete user: {user_id}")
                return False, None
                
        except Exception as e:
            logger.error(f"❌ Failed to delete user: {str(e)}")
            return False, None
    
    def delete_user_by_email(self, email: str) -> tuple[bool, Optional[str]]:
        """
        Delete user by email from MongoDB
        
        Args:
            email: User email
            
        Returns:
            Tuple of (success: bool, firebase_uid: Optional[str])
        """
        try:
            user = self.collection.find_one({"email": email})
            
            if not user:
                logger.warning(f"User not found: {email}")
                return False, None
            
            firebase_uid = user.get('firebase_uid')
            
            result = self.collection.delete_one({"email": email})
            
            if result.deleted_count > 0:
                logger.info(f"✅ User deleted from MongoDB: {email}")
                return True, firebase_uid
            else:
                return False, None
                
        except Exception as e:
            logger.error(f"❌ Failed to delete user: {str(e)}")
            return False, None
    
    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[Dict]:
        """
        Get user by Firebase UID
        
        Args:
            firebase_uid: Firebase user ID
            
        Returns:
            User document if found
        """
        try:
            user = self.collection.find_one({"firebase_uid": firebase_uid})
            if user:
                user.pop('password', None)
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            logger.error(f"❌ Failed to get user by Firebase UID: {str(e)}")
            return None
    
    def sync_firebase_user(
        self,
        firebase_uid: str,
        email: str,
        full_name: str,
        role: str = UserRole.HR
    ) -> Optional[str]:
        """
        Sync Firebase user to MongoDB
        
        Args:
            firebase_uid: Firebase user ID
            email: User email
            full_name: User's full name
            role: User role (hr or employee)
            
        Returns:
            User ID (MongoDB _id)
        """
        try:
            # Check if user exists by Firebase UID
            existing = self.get_user_by_firebase_uid(firebase_uid)
            if existing:
                logger.info(f"Firebase user already synced: {email}")
                return existing['_id']
            
            # Check if user exists by email
            existing_email = self.get_user_by_email(email)
            if existing_email:
                # Update with Firebase UID
                self.collection.update_one(
                    {"email": email},
                    {"$set": {
                        "firebase_uid": firebase_uid,
                        "updated_at": datetime.utcnow()
                    }}
                )
                logger.info(f"Updated existing user with Firebase UID: {email}")
                return existing_email['_id']
            
            # Create new user (Firebase auth, no password needed in MongoDB)
            user_doc = {
                "email": email,
                "firebase_uid": firebase_uid,
                "full_name": full_name,
                "role": role,
                "password": None,  # Firebase handles authentication
                "company": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "last_login": datetime.utcnow()
            }
            
            result = self.collection.insert_one(user_doc)
            logger.info(f"✅ Firebase user synced to MongoDB: {email} (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to sync Firebase user: {str(e)}")
            return None
            
            return users
        except Exception as e:
            logger.error(f"❌ Failed to get users: {str(e)}")
            return []

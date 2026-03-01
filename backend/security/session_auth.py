"""
Session Authentication & Security
JWT-based session tokens with per-session isolation
"""

import jwt
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class SessionToken:
    """Session token data structure"""
    session_id: str
    interview_id: str
    candidate_name: str
    job_description: str
    created_at: str
    expires_at: str
    token_hash: str
    permissions: Dict[str, bool]


class SessionAuthManager:
    """
    Manages JWT tokens for session isolation
    
    Features:
    - Unique JWT per session
    - Token-based authentication
    - Session permission management
    - Token revocation support
    - Memory isolation tracking
    """
    
    def __init__(self):
        """Initialize Session Auth Manager"""
        logger.info("🔐 Initializing SessionAuthManager")
        
        # JWT secret key
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
        self.jwt_algorithm = "HS256"
        self.token_expiry_hours = 24
        
        # MongoDB connection
        self.mongo_uri = os.getenv("MONGODB_ATLAS_URI")
        self.client = None
        self.db = None
        self.tokens_collection = None
        
        # In-memory token cache
        self.active_tokens: Dict[str, SessionToken] = {}
        
        self._connect_db()
        
        logger.info("✅ SessionAuthManager initialized")
        logger.info(f"   Token expiry: {self.token_expiry_hours} hours")
    
    def _connect_db(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
            self.db = self.client[mongo_db_name]
            self.tokens_collection = self.db['session_tokens']
            
            # Create indexes
            self.tokens_collection.create_index("session_id", unique=True)
            self.tokens_collection.create_index("token_hash")
            self.tokens_collection.create_index("expires_at")
            
            logger.info("✅ Connected to MongoDB for token management")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def generate_session_token(
        self,
        session_id: str,
        interview_id: str,
        candidate_name: str,
        job_description: str,
        permissions: Optional[Dict[str, bool]] = None
    ) -> Tuple[str, SessionToken]:
        """
        Generate unique JWT token for session
        
        Args:
            session_id: Unique session identifier
            interview_id: Interview identifier
            candidate_name: Candidate name
            job_description: Job description
            permissions: Session permissions
            
        Returns:
            Tuple of (jwt_token, session_token_object)
        """
        try:
            logger.info(f"🔑 Generating session token for: {session_id}")
            
            # Default permissions
            if permissions is None:
                permissions = {
                    "read": True,
                    "write": True,
                    "delete": False,
                    "analyze": True,
                    "export": True
                }
            
            # Create token data
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(hours=self.token_expiry_hours)
            
            # Generate unique token hash
            token_hash = hashlib.sha256(
                f"{session_id}{interview_id}{created_at.isoformat()}{secrets.token_hex(16)}".encode()
            ).hexdigest()
            
            # JWT payload
            payload = {
                "session_id": session_id,
                "interview_id": interview_id,
                "candidate_name": candidate_name,
                "job_description": job_description,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "token_hash": token_hash,
                "permissions": permissions,
                "iat": created_at.timestamp(),
                "exp": expires_at.timestamp()
            }
            
            # Generate JWT
            jwt_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            # Create session token object
            session_token = SessionToken(
                session_id=session_id,
                interview_id=interview_id,
                candidate_name=candidate_name,
                job_description=job_description,
                created_at=created_at.isoformat(),
                expires_at=expires_at.isoformat(),
                token_hash=token_hash,
                permissions=permissions
            )
            
            # Store in MongoDB
            self.tokens_collection.insert_one({
                **asdict(session_token),
                "jwt_token": jwt_token,
                "status": "active",
                "revoked": False
            })
            
            # Cache in memory
            self.active_tokens[session_id] = session_token
            
            logger.info(f"✅ Session token generated: {session_id}")
            logger.info(f"   Token hash: {token_hash[:16]}...")
            logger.info(f"   Expires: {expires_at.isoformat()}")
            
            return jwt_token, session_token
            
        except Exception as e:
            logger.error(f"❌ Error generating session token: {e}", exc_info=True)
            raise
    
    def verify_session_token(self, jwt_token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Verify JWT token
        
        Args:
            jwt_token: JWT token to verify
            
        Returns:
            Tuple of (valid, payload, error_message)
        """
        try:
            logger.debug(f"🔍 Verifying session token...")
            
            # Decode JWT
            payload = jwt.decode(jwt_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check expiration
            expires_at = datetime.fromisoformat(payload['expires_at'])
            if datetime.utcnow() > expires_at:
                logger.warning(f"⚠️ Token expired: {payload['session_id']}")
                return False, None, "Token has expired"
            
            # Check if revoked
            token_doc = self.tokens_collection.find_one({
                "session_id": payload['session_id'],
                "token_hash": payload['token_hash']
            })
            
            if not token_doc:
                logger.warning(f"⚠️ Token not found in database: {payload['session_id']}")
                return False, None, "Token not found"
            
            if token_doc.get('revoked', False):
                logger.warning(f"⚠️ Token revoked: {payload['session_id']}")
                return False, None, "Token has been revoked"
            
            logger.debug(f"✅ Token verified: {payload['session_id']}")
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"⚠️ Token expired (JWT level)")
            return False, None, "Token has expired"
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid token: {e}")
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            logger.error(f"❌ Error verifying token: {e}", exc_info=True)
            return False, None, f"Verification error: {str(e)}"
    
    def revoke_session_token(self, session_id: str) -> bool:
        """
        Revoke session token
        
        Args:
            session_id: Session ID to revoke
            
        Returns:
            Success status
        """
        try:
            logger.info(f"🚫 Revoking session token: {session_id}")
            
            # Update in MongoDB
            result = self.tokens_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": "revoked",
                        "revoked": True,
                        "revoked_at": datetime.utcnow()
                    }
                }
            )
            
            # Remove from cache
            if session_id in self.active_tokens:
                del self.active_tokens[session_id]
            
            if result.modified_count > 0:
                logger.info(f"✅ Token revoked: {session_id}")
                return True
            else:
                logger.warning(f"⚠️ Token not found for revocation: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error revoking token: {e}", exc_info=True)
            return False
    
    def get_session_permissions(self, session_id: str) -> Optional[Dict[str, bool]]:
        """
        Get permissions for session
        
        Args:
            session_id: Session ID
            
        Returns:
            Permissions dict or None
        """
        try:
            # Check cache first
            if session_id in self.active_tokens:
                return self.active_tokens[session_id].permissions
            
            # Check database
            token_doc = self.tokens_collection.find_one({"session_id": session_id})
            if token_doc:
                return token_doc.get('permissions', {})
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting permissions: {e}")
            return None
    
    def check_permission(self, session_id: str, permission: str) -> bool:
        """
        Check if session has specific permission
        
        Args:
            session_id: Session ID
            permission: Permission to check (read, write, delete, analyze, export)
            
        Returns:
            True if permission granted
        """
        permissions = self.get_session_permissions(session_id)
        if permissions:
            return permissions.get(permission, False)
        return False
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            logger.info("🧹 Cleaning up expired tokens...")
            
            result = self.tokens_collection.delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })
            
            # Clean cache
            expired_sessions = [
                sid for sid, token in self.active_tokens.items()
                if datetime.fromisoformat(token.expires_at) < datetime.utcnow()
            ]
            for sid in expired_sessions:
                del self.active_tokens[sid]
            
            logger.info(f"✅ Cleaned up {result.deleted_count} expired tokens")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up tokens: {e}")
            return 0
    
    def get_active_sessions(self) -> int:
        """Get count of active sessions"""
        try:
            return self.tokens_collection.count_documents({
                "status": "active",
                "revoked": False,
                "expires_at": {"$gt": datetime.utcnow()}
            })
        except:
            return len(self.active_tokens)
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("✅ Closed MongoDB connection")


# Singleton instance
_session_auth_manager: Optional[SessionAuthManager] = None


def get_session_auth_manager() -> SessionAuthManager:
    """Get singleton SessionAuthManager instance"""
    global _session_auth_manager
    if _session_auth_manager is None:
        _session_auth_manager = SessionAuthManager()
    return _session_auth_manager

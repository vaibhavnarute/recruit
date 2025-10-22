"""
User Service - User management business logic

Placeholder for future user-related business logic
"""

from repositories.user_repository import UserRepository


class UserService:
    """Service for user-related operations"""
    
    def __init__(self):
        self.user_repo = UserRepository()

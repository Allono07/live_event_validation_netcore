"""User repository."""
from typing import Optional
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.model.query.filter_by(username=username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.model.query.filter_by(email=email).first()
    
    def username_exists(self, username: str) -> bool:
        """Check if username exists."""
        return self.model.query.filter_by(username=username).first() is not None
    
    def email_exists(self, email: str) -> bool:
        """Check if email exists."""
        return self.model.query.filter_by(email=email).first() is not None
    
    def get_active_users(self):
        """Get all active users."""
        return self.model.query.filter_by(is_active=True).all()

"""Authentication service."""
from typing import Optional
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    """Service for user authentication and authorization.
    
    Single Responsibility: Authentication logic only.
    """
    
    def __init__(self, user_repo: UserRepository = None):
        """Initialize with dependency injection."""
        self.user_repo = user_repo or UserRepository()
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password.
        
        Prototype rule: username == password
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        # Prototype authentication: username == password
        if username != password:
            return None
        
        # Get or create user
        user = self.user_repo.get_by_username(username)
        
        if not user:
            # Auto-create user for prototype
            user = self.user_repo.create(
                username=username,
                password=password,  # In production, hash this!
                is_active=True
            )
        elif not user.is_active:
            return None
        
        return user
    
    def register_user(self, username: str, password: str, email: str = None) -> Optional[User]:
        """Register a new user.
        
        Args:
            username: Desired username
            password: User's password
            email: Optional email
            
        Returns:
            User object if registration successful, None otherwise
        """
        # Check if username exists
        if self.user_repo.username_exists(username):
            return None
        
        # Check if email exists
        if email and self.user_repo.email_exists(email):
            return None
        
        # Create user
        user = self.user_repo.create(
            username=username,
            password=password,  # In production, hash this!
            email=email,
            is_active=True
        )
        
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.user_repo.get_by_id(user_id)
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account."""
        user = self.user_repo.update(user_id, is_active=False)
        return user is not None

"""App management service."""
from typing import List, Optional
from app.models.app import App
from app.repositories.app_repository import AppRepository
from app.repositories.validation_rule_repository import ValidationRuleRepository
from app.repositories.log_repository import LogRepository
import secrets


class AppService:
    """Service for app management operations.
    
    Single Responsibility: App management logic.
    """
    
    def __init__(self, app_repo: AppRepository = None):
        """Initialize with dependency injection."""
        self.app_repo = app_repo or AppRepository()
        self.validation_rule_repo = ValidationRuleRepository()
        self.log_repo = LogRepository()
    
    def create_app(self, user_id: int, name: str, description: str = None, 
                   app_id: str = None) -> tuple:
        """Create a new app.
        
        Args:
            user_id: ID of the owning user
            name: App name
            description: Optional description
            app_id: Optional custom app ID (auto-generated if not provided)
            
        Returns:
            Tuple of (success: bool, result: App or error message)
        """
        try:
            # Generate app_id if not provided
            if not app_id:
                app_id = self._generate_app_id()
            else:
                # Validate custom app_id
                if self.app_repo.app_id_exists(app_id):
                    return False, f"App ID '{app_id}' already exists. Please choose a different ID."
            
            # Ensure generated app_id is unique
            while not app_id or self.app_repo.app_id_exists(app_id):
                app_id = self._generate_app_id()
            
            app = self.app_repo.create(
                app_id=app_id,
                name=name,
                description=description,
                user_id=user_id,
                is_active=True
            )
            
            return True, app
        except Exception as e:
            return False, str(e)
    
    def get_user_apps(self, user_id: int) -> List[App]:
        """Get all apps for a user."""
        return self.app_repo.get_by_user(user_id)
    
    def get_app_by_id(self, app_id: str) -> Optional[App]:
        """Get app by app_id."""
        return self.app_repo.get_by_app_id(app_id)
    
    def update_app(self, app_id: str, **kwargs) -> Optional[App]:
        """Update app details."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return None
        
        # Update allowed fields
        allowed_fields = ['name', 'description', 'is_active']
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if update_data:
            app = self.app_repo.update(app.id, **update_data)
        
        return app
    
    def delete_app(self, app_id: str) -> bool:
        """Delete an app and all its associated data.
        
        This will delete:
        - All validation rules for this app
        - All logs/events for this app
        - The application itself
        
        Returns: True if successful, False if app not found
        """
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return False
        
        try:
            # Delete all validation rules for this app
            self.validation_rule_repo.delete_by_app(app.id)
            
            # Delete all logs for this app
            self.log_repo.delete_all_by_app(app.id)
            
            # Delete the app itself
            self.app_repo.delete(app.id)
            
            return True
        except Exception as e:
            print(f"Error deleting app {app_id}: {str(e)}")
            return False
    
    def user_owns_app(self, user_id: int, app_id: str) -> bool:
        """Check if user owns the app."""
        return self.app_repo.user_owns_app(user_id, app_id)
    
    @staticmethod
    def _generate_app_id(length: int = 12) -> str:
        """Generate a random app ID."""
        return secrets.token_urlsafe(length)[:length]

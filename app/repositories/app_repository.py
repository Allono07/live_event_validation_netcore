"""App repository."""
from typing import List, Optional
from app.models.app import App
from app.repositories.base_repository import BaseRepository


class AppRepository(BaseRepository[App]):
    """Repository for App entity operations."""
    
    def __init__(self):
        super().__init__(App)
    
    def get_by_app_id(self, app_id: str) -> Optional[App]:
        """Get app by app_id."""
        return self.model.query.filter_by(app_id=app_id).first()
    
    def get_by_user(self, user_id: int) -> List[App]:
        """Get all apps for a user."""
        return self.model.query.filter_by(user_id=user_id, is_active=True).all()
    
    def app_id_exists(self, app_id: str) -> bool:
        """Check if app_id exists."""
        return self.model.query.filter_by(app_id=app_id).first() is not None
    
    def get_active_apps(self) -> List[App]:
        """Get all active apps."""
        return self.model.query.filter_by(is_active=True).all()
    
    def user_owns_app(self, user_id: int, app_id: str) -> bool:
        """Check if user owns the app."""
        app = self.get_by_app_id(app_id)
        return app is not None and app.user_id == user_id

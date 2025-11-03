"""Validation Rule repository."""
from typing import List
from app.models.validation_rule import ValidationRule
from app.repositories.base_repository import BaseRepository
from config.database import db


class ValidationRuleRepository(BaseRepository[ValidationRule]):
    """Repository for ValidationRule entity operations."""
    
    def __init__(self):
        super().__init__(ValidationRule)
    
    def get_by_app(self, app_id: int) -> List[ValidationRule]:
        """Get all validation rules for an app."""
        return self.model.query.filter_by(app_id=app_id).all()
    
    def get_by_event(self, app_id: int, event_name: str) -> List[ValidationRule]:
        """Get validation rules for a specific event."""
        return self.model.query.filter_by(
            app_id=app_id, 
            event_name=event_name.lower()
        ).all()
    
    def delete_by_app(self, app_id: int) -> int:
        """Delete all validation rules for an app. Returns count of deleted rules."""
        count = self.model.query.filter_by(app_id=app_id).delete()
        db.session.commit()
        return count
    
    def bulk_create(self, rules: List[dict]) -> List[ValidationRule]:
        """Create multiple validation rules at once."""
        entities = [self.model(**rule) for rule in rules]
        db.session.add_all(entities)
        db.session.commit()
        return entities
    
    def get_event_names(self, app_id: int) -> List[str]:
        """Get unique event names for an app."""
        results = db.session.query(ValidationRule.event_name).filter_by(
            app_id=app_id
        ).distinct().all()
        return [r[0] for r in results]

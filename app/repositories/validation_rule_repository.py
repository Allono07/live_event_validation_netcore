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
    
    def get_by_id(self, rule_id: int) -> ValidationRule:
        """Get a validation rule by ID."""
        return self.model.query.filter_by(id=rule_id).first()
    
    def update_rule(self, rule_id: int, **kwargs) -> ValidationRule:
        """Update a validation rule."""
        rule = self.get_by_id(rule_id)
        if not rule:
            return None
        
        # Update allowed fields
        allowed_fields = ['event_name', 'field_name', 'data_type', 'is_required', 'expected_pattern', 'condition']
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if update_data:
            for key, value in update_data.items():
                setattr(rule, key, value)
            db.session.commit()
        
        return rule
    
    def delete_by_id(self, rule_id: int) -> bool:
        """Delete a validation rule by ID. Returns True if successful."""
        rule = self.get_by_id(rule_id)
        if not rule:
            return False
        
        db.session.delete(rule)
        db.session.commit()
        return True
    
    def delete_by_event(self, app_id: int, event_name: str) -> int:
        """Delete all validation rules for a specific event. Returns count of deleted rules."""
        count = self.model.query.filter_by(
            app_id=app_id,
            event_name=event_name.lower()
        ).delete()
        db.session.commit()
        return count

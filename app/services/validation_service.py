"""Validation service."""
from typing import List, Dict, Any
from app.models.validation_rule import ValidationRule
from app.repositories.validation_rule_repository import ValidationRuleRepository
from app.repositories.app_repository import AppRepository
from app.validators.csv_parser import CSVParser


class ValidationService:
    """Service for managing validation rules.
    
    Single Responsibility: Validation rule management.
    """
    
    def __init__(self, validation_repo: ValidationRuleRepository = None,
                 app_repo: AppRepository = None):
        """Initialize with dependency injection."""
        self.validation_repo = validation_repo or ValidationRuleRepository()
        self.app_repo = app_repo or AppRepository()
        self.csv_parser = CSVParser()
    
    def upload_validation_rules(self, app_id: str, csv_content: str) -> Dict[str, Any]:
        """Upload and save validation rules from CSV content.
        
        Args:
            app_id: Application ID
            csv_content: CSV file content
            
        Returns:
            Dictionary with upload results
        """
        # Get app
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return {'success': False, 'error': 'App not found'}
        
        try:
            # Parse CSV
            rules = self.csv_parser.parse_csv_content(csv_content)
            
            if not rules:
                return {'success': False, 'error': 'No valid rules found in CSV'}
            
            # Delete existing rules for this app
            deleted_count = self.validation_repo.delete_by_app(app.id)
            
            # Prepare rules for bulk insert
            rule_data = [
                {
                    'app_id': app.id,
                    'event_name': rule['event_name'],
                    'field_name': rule['field_name'],
                    'data_type': rule['data_type'],
                    'is_required': rule['is_required'],
                    'condition': rule.get('condition', {})
                }
                for rule in rules
            ]
            
            # Bulk create rules
            created_rules = self.validation_repo.bulk_create(rule_data)
            
            return {
                'success': True,
                'rules_count': len(created_rules),
                'deleted_count': deleted_count,
                'event_names': list(set(r['event_name'] for r in rules))
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_app_rules(self, app_id: str) -> List[ValidationRule]:
        """Get all validation rules for an app."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return []
        return self.validation_repo.get_by_app(app.id)
    
    def get_event_rules(self, app_id: str, event_name: str) -> List[ValidationRule]:
        """Get validation rules for a specific event."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return []
        return self.validation_repo.get_by_event(app.id, event_name)
    
    def get_event_names(self, app_id: str) -> List[str]:
        """Get all unique event names for an app."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return []
        return self.validation_repo.get_event_names(app.id)
    
    def has_validation_rules(self, app_id: str) -> bool:
        """Check if app has any validation rules."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return False
        rules = self.validation_repo.get_by_app(app.id)
        return len(rules) > 0

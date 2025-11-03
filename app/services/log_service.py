"""Log processing service."""
from typing import Dict, Any, List, Tuple
from datetime import datetime
from app.models.log_entry import LogEntry
from app.repositories.log_repository import LogRepository
from app.repositories.app_repository import AppRepository
from app.services.validation_service import ValidationService
from app.validators.event_validator import EventValidator


class LogService:
    """Service for processing and storing log entries.
    
    Single Responsibility: Log processing and validation.
    """
    
    def __init__(self, log_repo: LogRepository = None,
                 app_repo: AppRepository = None,
                 validation_service: ValidationService = None):
        """Initialize with dependency injection."""
        self.log_repo = log_repo or LogRepository()
        self.app_repo = app_repo or AppRepository()
        self.validation_service = validation_service or ValidationService()
        self.event_validator = EventValidator()
    
    def process_log(self, app_id: str, log_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Process incoming log entry.
        
        Args:
            app_id: Application ID
            log_data: Log data containing event_name and payload
            
        Returns:
            Tuple of (success, result_data)
        """
        # Get app
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return False, {'error': 'App not found'}
        
        # Extract event data
        event_name = log_data.get('event_name') or log_data.get('eventName') or log_data.get('event')
        payload = log_data.get('payload', {})
        
        if not event_name:
            return False, {'error': 'Missing event_name in log data'}
        
        # Normalize event name
        event_name = event_name.lower()
        
        # Get validation rules for this event
        validation_rules = self.validation_service.get_event_rules(app_id, event_name)
        
        if not validation_rules:
            # No validation rules - store as error
            log_entry = self.log_repo.create(
                app_id=app.id,
                event_name=event_name,
                payload=payload,
                validation_status='error',
                validation_results=[{
                    'error': 'No validation rules found for this event'
                }]
            )
            return True, {
                'status': 'error',
                'message': 'No validation rules found for this event',
                'log_id': log_entry.id
            }
        
        # Convert validation rules to dict format
        rules_dict = [
            {
                'field_name': rule.field_name,
                'data_type': rule.data_type,
                'is_required': rule.is_required,
                'condition': rule.condition
            }
            for rule in validation_rules
        ]
        
        # Validate the event
        try:
            overall_status, validation_results = self.event_validator.validate_event(
                event_name, payload, rules_dict
            )
        except Exception as e:
            # Validation error
            log_entry = self.log_repo.create(
                app_id=app.id,
                event_name=event_name,
                payload=payload,
                validation_status='error',
                validation_results=[{'error': str(e)}]
            )
            return True, {
                'status': 'error',
                'message': f'Validation error: {str(e)}',
                'log_id': log_entry.id
            }
        
        # Store log entry
        log_entry = self.log_repo.create(
            app_id=app.id,
            event_name=event_name,
            payload=payload,
            validation_status=overall_status,
            validation_results=validation_results
        )
        
        return True, {
            'status': overall_status,
            'log_id': log_entry.id,
            'validation_results': validation_results
        }
    
    def get_app_logs(self, app_id: str, limit: int = 100) -> List[LogEntry]:
        """Get recent logs for an app."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return []
        return self.log_repo.get_by_app(app.id, limit)
    
    def get_validation_stats(self, app_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get validation statistics for an app."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return {'total': 0, 'valid': 0, 'invalid': 0, 'error': 0}
        return self.log_repo.get_stats(app.id, hours)
    
    def get_recent_logs(self, app_id: str, hours: int = 24, limit: int = 1000) -> List[LogEntry]:
        """Get logs from the last N hours."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return []
        return self.log_repo.get_recent_logs(app.id, hours, limit)

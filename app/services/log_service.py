"""Log processing service."""
from typing import Dict, Any, List, Tuple
from datetime import datetime
from app.models.log_entry import LogEntry
from app.repositories.log_repository import LogRepository
from app.repositories.app_repository import AppRepository
from app.services.validation_service import ValidationService
from app.validators.event_validator import EventValidator
from config.database import db


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
            # No validation rules - apply permissive fallback validator (from beta2.py behavior)
            overall_status, validation_results = self.event_validator.validate_unknown_event(event_name, payload)
            # Store log entry with fallback results
            log_entry = self.log_repo.create(
                app_id=app.id,
                event_name=event_name,
                payload=payload,
                validation_status=overall_status,
                validation_results=validation_results
            )
            
            # Compute payload hash for deduplication (AFTER creating entry)
            payload_hash = self.log_repo._compute_payload_hash(payload)
            log_entry.payload_hash = payload_hash
            db.session.commit()
            
            # Delete older duplicates, keep this new entry
            self.log_repo.delete_duplicate_older_entries(
                app.id, event_name, payload, keep_id=log_entry.id
            )
            
            return True, log_entry.to_dict()
        
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
            # Validation error - persist and return the stored log
            log_entry = self.log_repo.create(
                app_id=app.id,
                event_name=event_name,
                payload=payload,
                validation_status='error',
                validation_results=[{'error': str(e)}]
            )
            
            # Compute payload hash for deduplication (AFTER creating entry)
            payload_hash = self.log_repo._compute_payload_hash(payload)
            log_entry.payload_hash = payload_hash
            db.session.commit()
            
            # Delete older duplicates, keep this new entry
            self.log_repo.delete_duplicate_older_entries(
                app.id, event_name, payload, keep_id=log_entry.id
            )
            
            return True, log_entry.to_dict()
        
        # Store log entry
        log_entry = self.log_repo.create(
            app_id=app.id,
            event_name=event_name,
            payload=payload,
            validation_status=overall_status,
            validation_results=validation_results
        )
        
        # Compute payload hash for deduplication (AFTER creating entry)
        payload_hash = self.log_repo._compute_payload_hash(payload)
        log_entry.payload_hash = payload_hash
        db.session.commit()
        
        # Delete older duplicates, keep this new entry
        self.log_repo.delete_duplicate_older_entries(
            app.id, event_name, payload, keep_id=log_entry.id
        )
        
        # Return the full stored log entry dictionary so callers (and WebSocket emits)
        # have access to event_name, payload, validation_results and created_at
        return True, log_entry.to_dict()
    
    def get_app_logs(self, app_id: str, limit: int = 100) -> List[LogEntry]:
        """Get recent logs for an app."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return []
        return self.log_repo.get_by_app(app.id, limit)
    
    def get_app_logs_paginated(self, app_id: str, page: int = 1, limit: int = 50) -> Tuple[List[LogEntry], int]:
        """Get paginated logs for an app.
        
        Returns: (logs, total_count)
        """
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return [], 0
        return self.log_repo.get_by_app_paginated(app.id, page, limit)
    
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

    def delete_all_logs(self, app_id: str) -> Tuple[bool, int]:
        """Delete all logs for an app. Returns (success, deleted_count)."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return False, 0
        deleted = self.log_repo.delete_all_by_app(app.id)
        return True, deleted
    
    def get_distinct_event_names(self, app_id: str) -> List[str]:
        """Get distinct event names captured in logs for an app."""
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return []
        return self.log_repo.get_distinct_event_names(app.id)
    
    def get_fully_valid_events(self, app_id: str, hours: int = 24) -> List[str]:
        """Get list of events where the latest instance has all valid fields.
        
        Args:
            app_id: Application ID
            hours: Time window in hours (default 24)
            
        Returns:
            List of event names that are fully valid in their latest instance
        """
        app = self.app_repo.get_by_app_id(app_id)
        if not app:
            return []
        return self.log_repo.get_fully_valid_events(app.id, hours)

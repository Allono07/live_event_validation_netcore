"""Log Entry repository."""
from typing import List, Optional
from datetime import datetime, timedelta
from hashlib import sha256
import json
from app.models.log_entry import LogEntry
from app.repositories.base_repository import BaseRepository
from config.database import db


class LogRepository(BaseRepository[LogEntry]):
    """Repository for LogEntry entity operations."""
    
    def __init__(self):
        super().__init__(LogEntry)
    
    def get_by_app(self, app_id: int, limit: int = 100) -> List[LogEntry]:
        """Get recent logs for an app."""
        return self.model.query.filter_by(app_id=app_id)\
            .order_by(LogEntry.created_at.desc())\
            .limit(limit).all()
    
    def get_by_status(self, app_id: int, status: str, limit: int = 100) -> List[LogEntry]:
        """Get logs by validation status."""
        return self.model.query.filter_by(app_id=app_id, validation_status=status)\
            .order_by(LogEntry.created_at.desc())\
            .limit(limit).all()
    
    def get_recent_logs(self, app_id: int, hours: int = 24, limit: int = 1000) -> List[LogEntry]:
        """Get logs from the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return self.model.query.filter(
            LogEntry.app_id == app_id,
            LogEntry.created_at >= since
        ).order_by(LogEntry.created_at.desc()).limit(limit).all()
    
    def get_stats(self, app_id: int, hours: int = 24) -> dict:
        """Get validation statistics for an app.
        
        Stats breakdown:
        - total: Total unique events (by event_name) that have been captured
        - valid: Unique events where ALL instances have ALL fields passed validation
        - invalid: Unique events where at least ONE instance has at least ONE field failed
        - error: Events where validation threw an error or had issues
        
        CRITICAL: An event is "Passed" only if EVERY instance of it has EVERY field valid.
        If you have 10 UserLogin events and even 1 has a field that's invalid, UserLogin is "Failed".
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get all logs in the time window
        logs = db.session.query(LogEntry).filter(
            LogEntry.app_id == app_id,
            LogEntry.created_at >= since
        ).all()
        
        # Group logs by event_name to track the best and worst status for each event
        event_statuses = {}  # event_name -> list of (validation_status, all_fields_valid)
        
        for log in logs:
            event_name = log.event_name
            
            # Check if all fields are valid for this specific log entry
            all_fields_valid = False
            if log.validation_status == 'valid':
                if log.validation_results and isinstance(log.validation_results, list):
                    all_fields_valid = all(
                        result.get('validationStatus') == 'Valid' 
                        for result in log.validation_results
                    )
                else:
                    all_fields_valid = True
            
            # Initialize if not seen before
            if event_name not in event_statuses:
                event_statuses[event_name] = {
                    'has_error': False,
                    'has_invalid': False,
                    'all_instances_fully_valid': True
                }
            
            # Update the tracking for this event
            if log.validation_status == 'error':
                event_statuses[event_name]['has_error'] = True
            elif log.validation_status == 'invalid':
                event_statuses[event_name]['has_invalid'] = True
                event_statuses[event_name]['all_instances_fully_valid'] = False
            elif log.validation_status == 'valid':
                if not all_fields_valid:
                    event_statuses[event_name]['has_invalid'] = True
                    event_statuses[event_name]['all_instances_fully_valid'] = False
        
        # Now categorize each unique event based on its worst status
        total_count = 0
        valid_count = 0
        invalid_count = 0
        error_count = 0
        
        for event_name, status_info in event_statuses.items():
            total_count += 1
            
            if status_info['has_error']:
                error_count += 1
            elif status_info['has_invalid'] or not status_info['all_instances_fully_valid']:
                invalid_count += 1
            else:
                valid_count += 1
        
        return {
            'total': total_count,
            'valid': valid_count,
            'invalid': invalid_count,
            'error': error_count
        }
    
    def delete_old_logs(self, app_id: int, days: int = 30) -> int:
        """Delete logs older than N days. Returns count of deleted logs."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = self.model.query.filter(
            LogEntry.app_id == app_id,
            LogEntry.created_at < cutoff
        ).delete()
        db.session.commit()
        return count

    def delete_all_by_app(self, app_id: int) -> int:
        """Delete all logs for a given app. Returns count of deleted logs."""
        count = self.model.query.filter(
            LogEntry.app_id == app_id
        ).delete()
        db.session.commit()
        return count
    
    def get_distinct_event_names(self, app_id: int) -> List[str]:
        """Get distinct event names captured for this app."""
        results = db.session.query(LogEntry.event_name).filter(
            LogEntry.app_id == app_id,
            LogEntry.event_name.isnot(None)
        ).distinct().all()
        return [r[0] for r in results if r[0]]
    
    def _compute_payload_hash(self, payload: dict) -> str:
        """Compute hash of payload (eventName + payload sub-object only, ignore metadata).
        
        Option A: Hash only eventName and payload, ignore transient metadata like:
        - identity (user identifier)
        - eventTime (when event occurred)
        - sessionId (session identifier)
        - Other metadata fields
        
        This allows deduplication based on core event + payload data.
        """
        if not isinstance(payload, dict):
            return ""
        
        # Extract only eventName and payload sub-object
        essential_data = {
            'eventName': payload.get('eventName', ''),
            'payload': payload.get('payload', {})
        }
        
        # Create deterministic JSON string
        payload_json = json.dumps(essential_data, sort_keys=True, default=str)
        
        # Compute SHA256 hash
        return sha256(payload_json.encode()).hexdigest()
    
    def find_duplicate(self, app_id: int, event_name: str, payload: dict) -> Optional[LogEntry]:
        """Find existing log entry with same payload hash.
        
        Returns the most recent entry with matching payload hash, or None if no match.
        """
        payload_hash = self._compute_payload_hash(payload)
        if not payload_hash:
            return None
        
        existing = self.model.query.filter_by(
            app_id=app_id,
            event_name=event_name,
            payload_hash=payload_hash
        ).order_by(LogEntry.created_at.desc()).first()
        
        return existing
    
    def delete_duplicate_older_entries(self, app_id: int, event_name: str, 
                                       payload: dict, keep_id: int) -> int:
        """Delete all duplicate entries EXCEPT the one with keep_id.
        
        Finds all entries with same payload hash and deletes older ones,
        keeping only the entry with the specified keep_id.
        
        Returns count of deleted entries.
        """
        payload_hash = self._compute_payload_hash(payload)
        if not payload_hash:
            return 0
        
        # Find all entries with same payload hash EXCEPT keep_id
        duplicates = self.model.query.filter(
            LogEntry.app_id == app_id,
            LogEntry.event_name == event_name,
            LogEntry.payload_hash == payload_hash,
            LogEntry.id != keep_id
        ).all()
        
        count = len(duplicates)
        for entry in duplicates:
            db.session.delete(entry)
        
        db.session.commit()
        return count
    
    def get_by_app_paginated(self, app_id: int, page: int = 1, limit: int = 50) -> tuple:
        """Get paginated logs for an app.
        
        Returns: (logs, total_count)
        """
        query = self.model.query.filter_by(app_id=app_id)\
            .order_by(LogEntry.created_at.desc())
        
        total = query.count()
        offset = (page - 1) * limit
        
        logs = query.offset(offset).limit(limit).all()
        
        return logs, total

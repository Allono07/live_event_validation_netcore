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
        - valid: Unique events where the LATEST instance has ALL fields passed validation
        - invalid: Unique events where the LATEST instance has at least ONE field failed
        - error: Events where the LATEST instance had validation errors
        
        NEW BEHAVIOR: An event is "Passed" if the MOST RECENT instance is fully valid.
        This allows events to "recover" after payload issues are fixed.
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get all logs in the time window, ordered by created_at DESC (newest first)
        logs = db.session.query(LogEntry).filter(
            LogEntry.app_id == app_id,
            LogEntry.created_at >= since
        ).order_by(LogEntry.created_at.desc()).all()
        
        # Track the LATEST (most recent) instance of each event
        latest_event_status = {}  # event_name -> (validation_status, all_fields_valid)
        
        for log in logs:
            event_name = log.event_name
            
            # Skip if we've already seen a more recent instance of this event
            if event_name in latest_event_status:
                continue
            
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
            
            # Store the latest instance's status
            latest_event_status[event_name] = {
                'validation_status': log.validation_status,
                'all_fields_valid': all_fields_valid
            }
        
        # Now categorize each unique event based on its LATEST status
        total_count = 0
        valid_count = 0
        invalid_count = 0
        error_count = 0
        
        for event_name, status_info in latest_event_status.items():
            total_count += 1
            
            if status_info['validation_status'] == 'error':
                error_count += 1
            elif status_info['validation_status'] == 'invalid' or not status_info['all_fields_valid']:
                invalid_count += 1
            else:
                # validation_status == 'valid' AND all_fields_valid == True
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
    
    def get_fully_valid_events(self, app_id: int, hours: int = 24) -> List[str]:
        """Get list of events where the latest instance has all fields valid.
        
        Returns list of event names where:
        1. The event has validation rules (is in the CSV)
        2. The most recent instance is fully valid
        3. The event is a user event (eventId=0)
        """
        from datetime import datetime, timedelta
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get all logs in the time window, ordered by created_at DESC (newest first)
        logs = db.session.query(LogEntry).filter(
            LogEntry.app_id == app_id,
            LogEntry.created_at >= since
        ).order_by(LogEntry.created_at.desc()).all()
        
        # Track the LATEST instance of each event
        latest_event_status = {}
        
        for log in logs:
            event_name = log.event_name
            
            # Skip if we've already seen a more recent instance
            if event_name in latest_event_status:
                continue
            
            # Skip system events (eventId != 0)
            # Check if this is a user event by looking at validation_results
            is_user_event = False
            if log.validation_results and isinstance(log.validation_results, list):
                # Check if event has validation rules (not an "extra event")
                # Events with rules will have validation_results, system events won't
                has_validation_rules = any(
                    result.get('validationStatus') not in ['Extra event (not in sheet)', 'Payload from extra event']
                    for result in log.validation_results
                )
                if has_validation_rules:
                    is_user_event = True
            
            # Skip if not a user event with validation rules
            if not is_user_event:
                continue
            
            # Check if all fields are valid for this log
            all_fields_valid = False
            if log.validation_status == 'valid':
                if log.validation_results and isinstance(log.validation_results, list):
                    all_fields_valid = all(
                        result.get('validationStatus') == 'Valid'
                        for result in log.validation_results
                    )
                else:
                    all_fields_valid = True
            
            latest_event_status[event_name] = all_fields_valid
        
        # Return only events where latest instance is fully valid
        return [event_name for event_name, is_valid in latest_event_status.items() if is_valid]
    
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

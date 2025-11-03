"""Log Entry repository."""
from typing import List, Optional
from datetime import datetime, timedelta
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
        """Get validation statistics for an app."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        total = db.session.query(db.func.count(LogEntry.id)).filter(
            LogEntry.app_id == app_id,
            LogEntry.created_at >= since
        ).scalar()
        
        valid = db.session.query(db.func.count(LogEntry.id)).filter(
            LogEntry.app_id == app_id,
            LogEntry.validation_status == 'valid',
            LogEntry.created_at >= since
        ).scalar()
        
        invalid = db.session.query(db.func.count(LogEntry.id)).filter(
            LogEntry.app_id == app_id,
            LogEntry.validation_status == 'invalid',
            LogEntry.created_at >= since
        ).scalar()
        
        error = db.session.query(db.func.count(LogEntry.id)).filter(
            LogEntry.app_id == app_id,
            LogEntry.validation_status == 'error',
            LogEntry.created_at >= since
        ).scalar()
        
        return {
            'total': total or 0,
            'valid': valid or 0,
            'invalid': invalid or 0,
            'error': error or 0
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

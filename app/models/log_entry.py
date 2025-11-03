"""Log Entry model."""
from datetime import datetime
from config.database import db


class LogEntry(db.Model):
    """Log entries received from mobile apps."""
    
    __tablename__ = 'log_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'), nullable=False)
    event_name = db.Column(db.String(200), nullable=False, index=True)
    payload = db.Column(db.JSON, nullable=False)  # Raw payload data
    validation_status = db.Column(db.String(20), nullable=False, index=True)  # valid, invalid, error
    validation_results = db.Column(db.JSON, nullable=True)  # Detailed validation results
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Composite indexes for faster queries
    __table_args__ = (
        db.Index('idx_app_status', 'app_id', 'validation_status'),
        db.Index('idx_app_event_time', 'app_id', 'event_name', 'created_at'),
    )
    
    def __repr__(self):
        return f'<LogEntry {self.event_name} - {self.validation_status}>'
    
    def to_dict(self):
        """Convert log entry to dictionary."""
        return {
            'id': self.id,
            'app_id': self.app_id,
            'event_name': self.event_name,
            'payload': self.payload,
            'validation_status': self.validation_status,
            'validation_results': self.validation_results,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

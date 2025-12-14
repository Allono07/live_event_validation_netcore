"""App model."""
from datetime import datetime
from config.database import db


class App(db.Model):
    """Application entity for managing monitored apps."""
    
    __tablename__ = 'apps'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    platform = db.Column(db.String(50), default='android')
    sdk_type = db.Column(db.String(50), default='ce')
    
    # Relationships
    validation_rules = db.relationship('ValidationRule', backref='app', lazy='dynamic', 
                                      cascade='all, delete-orphan')
    log_entries = db.relationship('LogEntry', backref='app', lazy='dynamic',
                                 cascade='all, delete-orphan')
    fcm_tokens = db.relationship('FCMToken', backref='app', lazy='dynamic',
                                cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<App {self.app_id}: {self.name}>'
    
    def to_dict(self):
        """Convert app to dictionary."""
        return {
            'id': self.id,
            'app_id': self.app_id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'platform': self.platform,
            'sdk_type': self.sdk_type
        }

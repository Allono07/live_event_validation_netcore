"""FCM Token model."""
from datetime import datetime
from config.database import db


class FCMToken(db.Model):
    """FCM Tokens for push notifications."""
    
    __tablename__ = 'fcm_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'), nullable=False)
    token = db.Column(db.String(500), nullable=False)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FCMToken {self.token[:20]}...>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'app_id': self.app_id,
            'token': self.token,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }

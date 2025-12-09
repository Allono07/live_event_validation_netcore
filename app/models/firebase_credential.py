"""Firebase Credentials model."""
from datetime import datetime
from config.database import db


class FirebaseCredential(db.Model):
    """Stores Firebase service account credentials per app."""
    
    __tablename__ = 'firebase_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'), nullable=False, unique=True)
    credentials_json = db.Column(db.Text, nullable=False)  # Service account JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    app = db.relationship('App', backref='firebase_credential', uselist=False)
    
    def __repr__(self):
        return f'<FirebaseCredential app_id={self.app_id}>'

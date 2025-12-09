"""OTP (One-Time Password) model for email verification."""
from datetime import datetime, timedelta
from config.database import db


class OTP(db.Model):
    """Stores OTP for user registration and password reset."""
    
    __tablename__ = 'otps'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    otp_hash = db.Column(db.String(255), nullable=False)  # Hashed OTP
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OTP {self.email}>'
    
    def is_valid(self) -> bool:
        """Check if OTP is still valid (not expired and not used)."""
        return not self.is_used and datetime.utcnow() < self.expires_at
    
    def is_expired(self) -> bool:
        """Check if OTP has expired."""
        return datetime.utcnow() > self.expires_at

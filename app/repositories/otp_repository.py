"""OTP Repository for data access."""
from datetime import datetime
from app.models.otp import OTP
from app.repositories.base_repository import BaseRepository


class OTPRepository(BaseRepository):
    """Repository for OTP operations."""
    
    def __init__(self):
        super().__init__(OTP)
    
    def get_by_email(self, email: str) -> OTP:
        """Get most recent OTP for email."""
        return OTP.query.filter_by(email=email).order_by(OTP.created_at.desc()).first()
    
    def get_valid_otp(self, email: str) -> OTP:
        """Get valid (not expired, not used) OTP for email."""
        otp = self.get_by_email(email)
        if otp and otp.is_valid():
            return otp
        return None
    
    def create_otp(self, email: str, otp_hash: str, expires_at: datetime) -> OTP:
        """Create a new OTP record."""
        return self.create(email=email, otp_hash=otp_hash, expires_at=expires_at, is_used=False)
    
    def mark_as_used(self, otp_id: int) -> bool:
        """Mark OTP as used."""
        return self.update(otp_id, is_used=True) is not None
    
    def cleanup_expired_otps(self) -> int:
        """Delete expired OTPs. Returns count of deleted records."""
        from config.database import db
        count = OTP.query.filter(OTP.expires_at < datetime.utcnow(), OTP.is_used == False).delete()
        db.session.commit()
        return count

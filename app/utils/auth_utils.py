"""Utility functions for OTP generation, hashing, and verification."""
import secrets
import string
import bcrypt
from datetime import datetime, timedelta


def generate_otp(length: int = 6) -> str:
    """
    Generate a random numeric OTP.
    
    Args:
        length: Length of OTP (default 6 digits)
    
    Returns:
        Random numeric string of specified length
    """
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def hash_otp(otp: str) -> str:
    """
    Hash OTP using bcrypt.
    
    Args:
        otp: Plain text OTP
    
    Returns:
        Hashed OTP
    """
    return bcrypt.hashpw(otp.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_otp(otp: str, otp_hash: str) -> bool:
    """
    Verify OTP against its hash.
    
    Args:
        otp: Plain text OTP to verify
        otp_hash: Hashed OTP from database
    
    Returns:
        True if OTP matches, False otherwise
    """
    try:
        return bcrypt.checkpw(otp.encode('utf-8'), otp_hash.encode('utf-8'))
    except Exception:
        return False


def get_otp_expiry(minutes: int = 7) -> datetime:
    """
    Get OTP expiry datetime (default 7 minutes from now).
    
    Args:
        minutes: Minutes until expiry (default 7)
    
    Returns:
        Datetime when OTP should expire
    """
    return datetime.utcnow() + timedelta(minutes=minutes)


def is_strong_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*)
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if not any(c in "!@#$%^&*" for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*)"
    
    return True, "Password is strong"


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify password against its hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

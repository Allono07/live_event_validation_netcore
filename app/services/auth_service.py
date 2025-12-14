"""Authentication service with OTP-based email registration."""
from typing import Optional, Tuple
from flask import current_app
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.otp_repository import OTPRepository
from app.utils.auth_utils import (
    generate_otp, hash_otp, verify_otp, hash_password, verify_password,
    is_strong_password, get_otp_expiry
)
from app.utils.email_utils import send_otp_email, send_welcome_email, send_password_reset_email


class AuthService:
    """Service for user authentication with email and OTP.
    
    Handles registration via OTP, login with password, and password reset.
    """
    
    def __init__(self, user_repo: UserRepository = None, otp_repo: OTPRepository = None):
        """Initialize with dependency injection."""
        self.user_repo = user_repo or UserRepository()
        self.otp_repo = otp_repo or OTPRepository()
    
    def request_registration(self, email: str) -> Tuple[bool, str]:
        """
        Request registration by email - generates and sends OTP.
        
        Args:
            email: User's email address
        
        Returns:
            Tuple of (success, message)
        """
        # Validate email format
        if not email or '@' not in email:
            return False, "Invalid email address"
        
        # Check if email already registered
        if self.user_repo.email_exists(email):
            return False, "Email already registered"
        
        try:
            # Generate OTP
            otp = generate_otp()
            otp_hash = hash_otp(otp)
            expires_at = get_otp_expiry()
            
            # Save OTP to database
            self.otp_repo.create_otp(email, otp_hash, expires_at)
            
            # Send OTP via email
            if send_otp_email(email, otp):
                current_app.logger.info(f"OTP registration request for {email}")
                return True, f"OTP sent to {email}"
            else:
                return False, "Failed to send OTP email"
        except Exception as e:
            current_app.logger.error(f"Error in request_registration: {str(e)}")
            return False, "An error occurred while processing registration"
    
    def verify_otp_and_register(self, email: str, otp: str, password: str,
                                 password_confirm: str, username: str = None) -> Tuple[bool, str]:
        """
        Verify OTP and create user account.
        
        Args:
            email: User's email
            otp: 6-digit OTP from user
            password: New password
            password_confirm: Confirmation password
            username: Optional username (defaults to email prefix)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate passwords match
            if password != password_confirm:
                return False, "Passwords do not match"
            
            # Validate password strength
            is_strong, msg = is_strong_password(password)
            if not is_strong:
                return False, msg
            
            # Get valid OTP from database
            otp_record = self.otp_repo.get_valid_otp(email)
            
            if not otp_record:
                return False, "OTP not found or expired"
            
            # Verify OTP
            if not verify_otp(otp, otp_record.otp_hash):
                return False, "Invalid OTP"
            
            # Generate username if not provided
            if not username:
                username = email.split('@')[0]
            
            # Check username uniqueness
            if self.user_repo.username_exists(username):
                username = f"{username}_{otp_record.id}"  # Make unique
            
            # Hash password
            password_hash = hash_password(password)
            
            # Create user
            user = self.user_repo.create_user(email, username, password_hash)
            
            # Mark OTP as used
            self.otp_repo.mark_as_used(otp_record.id)
            
            # Send welcome email
            send_welcome_email(email, username)
            
            current_app.logger.info(f"New user registered: {email}")
            return True, "Account created successfully"
        except Exception as e:
            current_app.logger.error(f"Error registering user: {str(e)}")
            return False, "Failed to create account"
    
    def login(self, email: str, password: str) -> Tuple[bool, str, dict]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User's email
            password: User's password
        
        Returns:
            Tuple of (success, message, user_data)
        """
        try:
            # Get user by email
            user = self.user_repo.get_by_email(email)
            
            if not user:
                return False, "Invalid email or password", {}
            
            if not user.is_active:
                return False, "Account is inactive", {}
            
            # Verify password
            if not verify_password(password, user.password):
                return False, "Invalid email or password", {}
            
            current_app.logger.info(f"User logged in: {email}")
            return True, "Login successful", user.to_dict()
        except Exception as e:
            current_app.logger.error(f"Error during login: {str(e)}")
            return False, "An error occurred during login", {}
    
    def request_password_reset(self, email: str) -> Tuple[bool, str]:
        """
        Request password reset - generates and sends OTP.
        
        Args:
            email: User's email
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if user exists
            user = self.user_repo.get_by_email(email)
            if not user:
                # Don't reveal if email exists or not
                return True, "If account exists, check your email for OTP"
            
            # Generate and send OTP
            otp = generate_otp()
            otp_hash = hash_otp(otp)
            expires_at = get_otp_expiry()
            
            self.otp_repo.create_otp(email, otp_hash, expires_at)
            
            if send_password_reset_email(email, otp):
                current_app.logger.info(f"Password reset requested for {email}")
                return True, "Password reset OTP sent to your email"
            else:
                return False, "Failed to send reset email"
        except Exception as e:
            current_app.logger.error(f"Error in password reset request: {str(e)}")
            return False, "An error occurred"
    
    def reset_password(self, email: str, otp: str, new_password: str,
                       password_confirm: str) -> Tuple[bool, str]:
        """
        Reset password with OTP verification.
        
        Args:
            email: User's email
            otp: 6-digit OTP
            new_password: New password
            password_confirm: Confirmation password
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get user
            user = self.user_repo.get_by_email(email)
            if not user:
                return False, "User not found"
            
            # Validate passwords match
            if new_password != password_confirm:
                return False, "Passwords do not match"
            
            # Validate password strength
            is_strong, msg = is_strong_password(new_password)
            if not is_strong:
                return False, msg
            
            # Verify OTP
            otp_record = self.otp_repo.get_valid_otp(email)
            if not otp_record or not verify_otp(otp, otp_record.otp_hash):
                return False, "Invalid or expired OTP"
            
            # Update password
            password_hash = hash_password(new_password)
            user.password = password_hash
            self.user_repo.save(user)
            
            # Mark OTP as used
            self.otp_repo.mark_as_used(otp_record.id)
            
            current_app.logger.info(f"Password reset for {email}")
            return True, "Password reset successfully"
        except Exception as e:
            current_app.logger.error(f"Error resetting password: {str(e)}")
            return False, "Failed to reset password"
    
    # Legacy support for prototype authentication
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password (legacy).
        
        Prototype rule: username == password
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        # Prototype authentication: username == password
        if username != password:
            return None
        
        # Get or create user
        user = self.user_repo.get_by_username(username)
        
        if not user:
            # Auto-create user for prototype
            user = self.user_repo.create(
                username=username,
                password=password,  # In production, hash this!
                is_active=True
            )
        elif not user.is_active:
            return None
        
        return user

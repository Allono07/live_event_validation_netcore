"""Email utilities for sending OTP and notifications."""
import os
from flask_mail import Mail, Message
from flask import current_app


mail = Mail()


def init_email(app):
    """Initialize Flask-Mail with app."""
    mail.init_app(app)


def send_otp_email(email: str, otp: str) -> bool:
    """
    Send OTP via email.
    
    Args:
        email: Recipient email address
        otp: 6-digit OTP to send
    
    Returns:
        True if successful, False otherwise
    """
    # In development mode, log OTP instead of sending email
    is_dev = current_app.config.get('FLASK_ENV') == 'development'
    
    # if is_dev:
    #     current_app.logger.warning(f"🔐 DEV MODE - OTP for {email}: {otp}")
    #     return True
    
    try:
        msg = Message(
            subject='Your OTP for Registration',
            recipients=[email],
            html=f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Email Verification</h2>
                    <p>Your One-Time Password (OTP) is:</p>
                    <h1 style="color: #007bff; letter-spacing: 2px;">{otp}</h1>
                    <p><strong>This OTP is valid for 7 minutes.</strong></p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        This is an automated message, please do not reply.
                    </p>
                </body>
            </html>
            """
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False


def send_welcome_email(email: str, username: str) -> bool:
    """
    Send welcome email after successful registration.
    
    Args:
        email: Recipient email address
        username: Username
    
    Returns:
        True if successful, False otherwise
    """
    try:
        msg = Message(
            subject='Welcome to Live Validation Dashboard',
            recipients=[email],
            html=f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Welcome, {username}!</h2>
                    <p>Your account has been successfully created.</p>
                    <p>You can now log in to the <strong>Live Validation Dashboard</strong> and start managing your applications.</p>
                    <p><a href="{os.getenv('APP_URL', 'http://localhost:5001')}/auth/login" 
                          style="background-color: #007bff; color: white; padding: 10px 20px; 
                                 text-decoration: none; border-radius: 5px; display: inline-block;">
                        Login Now
                    </a></p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        If you have any questions, please contact our support team.
                    </p>
                </body>
            </html>
            """
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send welcome email to {email}: {str(e)}")
        return False


def send_password_reset_email(email: str, otp: str) -> bool:
    """
    Send password reset OTP via email.
    
    Args:
        email: Recipient email address
        otp: 6-digit OTP for password reset
    
    Returns:
        True if successful, False otherwise
    """
    # In development mode, log OTP instead of sending email
    is_dev = current_app.config.get('FLASK_ENV') == 'development'
    
    if is_dev:
        current_app.logger.warning(f"🔐 DEV MODE - Password Reset OTP for {email}: {otp}")
        return True
    
    try:
        msg = Message(
            subject='Password Reset Request',
            recipients=[email],
            html=f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Password Reset</h2>
                    <p>You requested a password reset. Use this OTP to proceed:</p>
                    <h1 style="color: #dc3545; letter-spacing: 2px;">{otp}</h1>
                    <p><strong>This OTP is valid for 7 minutes.</strong></p>
                    <p>If you didn't request this, please ignore this email and your password will remain unchanged.</p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        This is an automated message, please do not reply.
                    </p>
                </body>
            </html>
            """
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        return False

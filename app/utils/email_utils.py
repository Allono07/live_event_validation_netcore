"""Email utilities for sending OTP and notifications."""
import os
import socket
import time
from flask_mail import Mail, Message
from flask import current_app


mail = Mail()

# Set socket timeout - reduced to 30 seconds as DNS is now working
socket.setdefaulttimeout(30)


def init_email(app):
    """Initialize Flask-Mail with app."""
    # Respect configured suppression setting; do not override here
    # Configure timeouts for email
    app.config.setdefault('MAIL_CONNECT_TIMEOUT', 30)
    app.config.setdefault('MAIL_SEND_TIMEOUT', 30)

    mail.init_app(app)

    # Log email configuration (without password)
    protocol = "SSL" if app.config.get('MAIL_USE_SSL') else "TLS" if app.config.get('MAIL_USE_TLS') else "Plain"
    app.logger.info(f"📧 Email configured: {app.config.get('MAIL_SERVER')}:{app.config.get('MAIL_PORT')} ({protocol})")
    app.logger.info(f"📧 Sender: {app.config.get('MAIL_DEFAULT_SENDER')}")
    if app.config.get('MAIL_SUPPRESS_SEND'):
        app.logger.info("✳️ Email sending is suppressed; messages will not be sent.")
    if app.config.get('OTP_DELIVERY_MODE', 'log') == 'log':
        app.logger.info("✳️ OTP delivery mode is 'log' — OTPs will be logged instead of emailed.")


def send_otp_email(email: str, otp: str, max_retries: int = 3) -> bool:
    """
    Send OTP via email with retry logic.
    
    Args:
        email: Recipient email address
        otp: 6-digit OTP to send
        max_retries: Maximum number of retry attempts
    
    Returns:
        True if successful, False otherwise
    """
    
    # If configured to log-only or email suppression is enabled, do not send
    if current_app.config.get('OTP_DELIVERY_MODE', 'log') == 'log' or current_app.config.get('MAIL_SUPPRESS_SEND'):
        current_app.logger.info(f"🔐 OTP (log-only) for {email}: {otp}")
        return True

    attempt = 0
    last_error = None
    
    while attempt < max_retries:
        attempt += 1
        try:
            current_app.logger.info(f"📤 Attempt {attempt}/{max_retries} - Sending OTP to {email}...")
            
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
            current_app.logger.info(f"✅ OTP email sent successfully to {email}")
            return True
            
        except socket.timeout as e:
            last_error = f"Socket timeout: {str(e)}"
            current_app.logger.error(f"❌ Attempt {attempt}/{max_retries} - SMTP connection timed out for {email}")
            current_app.logger.error(f"⚠️ Troubleshooting: 1) Try port 465 with SSL instead of 587 with TLS, 2) Check Docker network connectivity, 3) Verify SMTP server allows connections from Docker")
            
        except Exception as e:
            last_error = str(e)
            error_msg = str(e)
            current_app.logger.error(f"❌ Attempt {attempt}/{max_retries} - Failed to send OTP email to {email}: {error_msg}")
            
            # Log specific error types for debugging
            if 'timed out' in error_msg.lower():
                current_app.logger.error(f"⚠️ Connection timeout - Try using port 465 with SSL")
            elif 'Lookup timed out' in error_msg or 'Name or service not known' in error_msg:
                current_app.logger.error(f"⚠️ DNS resolution error: {error_msg}")
            elif 'Connection refused' in error_msg:
                current_app.logger.error(f"⚠️ SMTP connection refused - Check port and firewall")
            elif 'Authentication failed' in error_msg or '[AUTHENTICATION FAILED]' in error_msg:
                current_app.logger.error(f"⚠️ SMTP auth error - Check credentials and app password")
                break  # Don't retry auth failures
        
        # Wait before retry
        if attempt < max_retries:
            wait_time = attempt * 3  # Progressive backoff: 3s, 6s, 9s
            current_app.logger.info(f"⏳ Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    current_app.logger.error(f"❌ Failed to send OTP after {max_retries} attempts. Last error: {last_error}")
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
    # In log-only or suppression mode, skip sending
    if current_app.config.get('OTP_DELIVERY_MODE', 'log') == 'log' or current_app.config.get('MAIL_SUPPRESS_SEND'):
        current_app.logger.info(f"📨 Welcome email suppressed (log-only) for {email}")
        return True
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
        current_app.logger.info(f"✅ Welcome email sent to {email}")
        return True
    except Exception as e:
        current_app.logger.error(f"❌ Failed to send welcome email to {email}: {str(e)}")
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
    # In log-only or suppression mode, skip sending but log OTP
    if current_app.config.get('OTP_DELIVERY_MODE', 'log') == 'log' or current_app.config.get('MAIL_SUPPRESS_SEND'):
        current_app.logger.info(f"🔁 Password reset OTP (log-only) for {email}: {otp}")
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
        current_app.logger.info(f"✅ Password reset email sent to {email}")
        return True
    except Exception as e:
        current_app.logger.error(f"❌ Failed to send password reset email to {email}: {str(e)}")
        return False
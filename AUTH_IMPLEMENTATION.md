# Email-Based Authentication Module

Complete authentication system with OTP-based email registration, secure password hashing, and password reset functionality.

## Features

### 1. Registration Flow
- User enters email
- System generates and sends 6-digit OTP (valid for 7 minutes)
- OTP stored as bcrypt hash in database
- User verifies OTP and sets password
- Account created with hashed password

### 2. Login Flow
- User logs in with email and password
- Password verified using bcrypt
- Session created for user
- Optional JWT token generation for API access

### 3. Password Reset
- User requests password reset via email
- OTP generated and sent
- User verifies OTP and sets new password
- Old password replaced with new bcrypt hash

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The following packages are included:
- `bcrypt==4.1.1` - Password hashing
- `Flask-JWT-Extended==4.5.3` - JWT tokens
- `Flask-Mail==0.9.1` - Email sending

### 2. Configure Email

Edit `.env` file (copy from `.env.example`):

```env
# Gmail Example
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourapp.com
```

**Gmail Setup:**
1. Enable 2-Factor Authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use generated password in `MAIL_PASSWORD`

**Other Email Providers:**
```env
# Outlook
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587

# SendGrid
MAIL_SERVER=smtp.sendgrid.net
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.your-api-key
```

### 3. Database Setup

Create OTP table (runs automatically on first startup):

```sql
CREATE TABLE otps (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(120) NOT NULL INDEX,
    otp_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### Registration

**Step 1: Request OTP**

```http
POST /auth/register
Content-Type: application/x-www-form-urlencoded

email=user@example.com
```

Or API endpoint:
```http
POST /auth/api/register
Content-Type: application/json

{
    "email": "user@example.com"
}
```

Response:
```json
{
    "success": true,
    "message": "OTP sent to user@example.com",
    "email": "user@example.com"
}
```

**Step 2: Verify OTP & Create Account**

```http
POST /auth/verify-otp
Content-Type: application/x-www-form-urlencoded

email=user@example.com
otp=123456
password=SecurePass123!
password_confirm=SecurePass123!
username=john_doe
```

Or API endpoint:
```http
POST /auth/api/verify-otp
Content-Type: application/json

{
    "email": "user@example.com",
    "otp": "123456",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "username": "john_doe"
}
```

### Login

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

email=user@example.com
password=SecurePass123!
remember_me=on
```

Or API endpoint:
```http
POST /auth/api/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "SecurePass123!"
}
```

Response:
```json
{
    "success": true,
    "message": "Login successful",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "user@example.com",
        "created_at": "2025-12-09T21:00:00",
        "is_active": true
    }
}
```

### Password Reset

**Step 1: Request Reset**

```http
POST /auth/forgot-password
Content-Type: application/x-www-form-urlencoded

email=user@example.com
```

Or API endpoint:
```http
POST /auth/api/forgot-password
Content-Type: application/json

{
    "email": "user@example.com"
}
```

**Step 2: Verify OTP & Reset**

```http
POST /auth/reset-password
Content-Type: application/x-www-form-urlencoded

email=user@example.com
otp=123456
password=NewSecurePass123!
password_confirm=NewSecurePass123!
```

Or API endpoint:
```http
POST /auth/api/reset-password
Content-Type: application/json

{
    "email": "user@example.com",
    "otp": "123456",
    "password": "NewSecurePass123!",
    "password_confirm": "NewSecurePass123!"
}
```

## Code Structure

### Models

**OTP Model** (`app/models/otp.py`)
- `email`: User's email
- `otp_hash`: Bcrypt hashed OTP
- `expires_at`: OTP expiration time
- `is_used`: Flag for used OTP
- `created_at`: Creation timestamp

```python
otp = OTP.query.filter_by(email='user@example.com').first()
if otp.is_valid():  # Not expired and not used
    # Process registration
```

**User Model** (enhanced)
- `email`: User email (unique)
- `username`: User username (unique, optional for registration)
- `password`: Bcrypt hashed password
- `is_active`: Account status
- `created_at`, `updated_at`: Timestamps

### Repositories

**OTPRepository** (`app/repositories/otp_repository.py`)
```python
otp_repo = OTPRepository()

# Get valid OTP
otp = otp_repo.get_valid_otp(email)

# Create OTP
otp = otp_repo.create_otp(email, otp_hash, expires_at)

# Mark as used
otp_repo.mark_as_used(otp_id)

# Cleanup expired
otp_repo.cleanup_expired_otps()
```

**UserRepository** (enhanced)
```python
user_repo = UserRepository()

# Get by email
user = user_repo.get_by_email('user@example.com')

# Create user
user = user_repo.create_user(email, username, password_hash)

# Check existence
exists = user_repo.email_exists('user@example.com')
```

### Services

**AuthService** (`app/services/auth_service.py`)
```python
auth_service = AuthService()

# Register request (send OTP)
success, msg = auth_service.request_registration('user@example.com')

# Verify and register
success, msg = auth_service.verify_otp_and_register(
    email='user@example.com',
    otp='123456',
    password='SecurePass123!',
    password_confirm='SecurePass123!'
)

# Login
success, msg, user_data = auth_service.login(
    email='user@example.com',
    password='SecurePass123!'
)

# Password reset request
success, msg = auth_service.request_password_reset('user@example.com')

# Reset password
success, msg = auth_service.reset_password(
    email='user@example.com',
    otp='123456',
    new_password='NewPass123!',
    password_confirm='NewPass123!'
)
```

### Utilities

**auth_utils.py** - Cryptographic functions
```python
from app.utils.auth_utils import (
    generate_otp,           # Generate 6-digit OTP
    hash_otp,              # Hash OTP with bcrypt
    verify_otp,            # Verify OTP against hash
    hash_password,         # Hash password with bcrypt
    verify_password,       # Verify password against hash
    is_strong_password,    # Validate password strength
    get_otp_expiry         # Get expiry datetime
)

# Example
otp = generate_otp()  # '123456'
otp_hash = hash_otp(otp)
verified = verify_otp('123456', otp_hash)  # True
```

**email_utils.py** - Email sending
```python
from app.utils.email_utils import (
    send_otp_email,        # Send OTP email
    send_welcome_email,    # Send welcome after registration
    send_password_reset_email  # Send password reset email
)

# Example
send_otp_email('user@example.com', '123456')
send_welcome_email('user@example.com', 'john_doe')
```

## Password Requirements

All passwords must meet these requirements:
- ✓ At least 8 characters
- ✓ One uppercase letter (A-Z)
- ✓ One lowercase letter (a-z)
- ✓ One number (0-9)
- ✓ One special character (!@#$%^&*)

Invalid password example:
```
"password123"  ✗ No uppercase, no special char
"Pass"         ✗ Too short
"PASSWORD123"  ✗ No lowercase
```

Valid password example:
```
"SecurePass123!"  ✓ Meets all requirements
```

## Security Features

### OTP Security
- ✓ OTP stored as bcrypt hash (not plaintext)
- ✓ 7-minute expiration
- ✓ One-time use (marked as used after verification)
- ✓ Auto-cleanup of expired OTPs

### Password Security
- ✓ Bcrypt hashing with salt (rounds=12)
- ✓ Password strength validation
- ✓ Passwords never stored in plaintext
- ✓ Password confirmation matching

### Email Security
- ✓ Flask-Mail with TLS encryption
- ✓ No credentials in logs
- ✓ HTML emails with proper formatting

### Session Security
- ✓ HttpOnly cookies (CSRF protection)
- ✓ SameSite=Lax (cross-site attacks)
- ✓ Session expiry (default 7 days)

## Error Handling

All endpoints return proper HTTP status codes:

| Status | Scenario |
|--------|----------|
| 200 | Success |
| 400 | Validation error (weak password, missing fields, etc.) |
| 401 | Authentication failed (invalid credentials) |
| 409 | Email already registered |

Error response example:
```json
{
    "success": false,
    "message": "Password must contain at least one special character (!@#$%^&*)"
}
```

## Testing

### Test Registration Flow
```bash
# 1. Register with email
curl -X POST http://localhost:5001/auth/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# 2. Check email for OTP (in development, check logs)
# 3. Verify OTP
curl -X POST http://localhost:5001/auth/api/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "otp":"123456",
    "password":"TestPass123!",
    "password_confirm":"TestPass123!"
  }'

# 4. Login
curl -X POST http://localhost:5001/auth/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}'
```

## Development Notes

### Email Testing
In development, set `TESTING=True` to see OTPs in console instead of sending emails:

```python
# In config.py
TESTING = os.environ.get('TESTING', False)
```

### Debugging
Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Database Cleanup
Remove expired OTPs:

```python
from app.repositories.otp_repository import OTPRepository
repo = OTPRepository()
deleted_count = repo.cleanup_expired_otps()
print(f"Deleted {deleted_count} expired OTPs")
```

## Future Enhancements

- [ ] JWT token endpoints (for API-only apps)
- [ ] Multi-factor authentication (SMS + Email)
- [ ] Account lockout after failed attempts
- [ ] Email verification during registration
- [ ] OAuth integration (Google, GitHub)
- [ ] Social login
- [ ] Account recovery options

## Troubleshooting

### OTP not sending
1. Check email credentials in `.env`
2. Verify MAIL_SERVER and MAIL_PORT
3. Check application logs for email errors
4. For Gmail: Use App Password, not regular password

### Password validation failing
1. Ensure 8+ characters
2. Check for uppercase, lowercase, digit, special char
3. Example: `SecurePass123!`

### OTP expired
1. OTP valid for 7 minutes
2. User must verify within time window
3. Request new OTP if expired

## Support

For issues or questions:
1. Check logs: `tail -f /var/log/app.log`
2. Verify email configuration
3. Test with curl commands
4. Check database tables exist


# Quick Start - Email Authentication Setup

## Step-by-Step Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Email Service

#### Option A: Gmail (Recommended for Development)

1. Enable 2-Factor Authentication on your Google Account
2. Generate App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer"
   - Copy the generated 16-character password

3. Add to `.env`:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_DEFAULT_SENDER=noreply@validation.app
```

#### Option B: Local Testing (No Email Required)

For testing without email:
```env
TESTING=True
# OTPs will be printed to console instead of emailing
```

### 3. Initialize Database

Restart the Flask application - tables will be created automatically:
```bash
python3 ./run.py
```

### 4. Test the Authentication System

#### Via Web Interface
1. Navigate to http://localhost:5001/auth/register
2. Enter email and follow prompts
3. Check console/email for OTP
4. Login at http://localhost:5001/auth/login

#### Via API (curl)

**Register:**
```bash
curl -X POST http://localhost:5001/auth/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@example.com"}'
```

**Verify OTP:**
```bash
curl -X POST http://localhost:5001/auth/api/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email":"testuser@example.com",
    "otp":"123456",
    "password":"SecurePass123!",
    "password_confirm":"SecurePass123!",
    "username":"testuser"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:5001/auth/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"testuser@example.com",
    "password":"SecurePass123!"
  }'
```

## Route Summary

| Route | Method | Purpose |
|-------|--------|---------|
| `/auth/register` | GET, POST | Registration page (email entry) |
| `/auth/verify-otp` | GET, POST | OTP verification & password setup |
| `/auth/login` | GET, POST | Login page |
| `/auth/forgot-password` | GET, POST | Password reset request |
| `/auth/reset-password` | GET, POST | Password reset confirmation |
| `/auth/logout` | POST | Logout (requires login) |
| `/auth/api/register` | POST | API: Request OTP |
| `/auth/api/verify-otp` | POST | API: Verify & Register |
| `/auth/api/login` | POST | API: Login |
| `/auth/api/forgot-password` | POST | API: Reset request |
| `/auth/api/reset-password` | POST | API: Reset password |

## Files Modified/Created

### New Models
- `app/models/otp.py` - OTP storage model

### New Repositories
- `app/repositories/otp_repository.py` - OTP data access

### Updated Repositories
- `app/repositories/user_repository.py` - Added `create_user()` method

### New Utilities
- `app/utils/auth_utils.py` - Password/OTP hashing and validation
- `app/utils/email_utils.py` - Email sending functions

### Updated Services
- `app/services/auth_service.py` - Complete rewrite with email/OTP auth

### New Controllers
- `app/controllers/auth_email_controller.py` - All auth routes

### New Templates
- `app/templates/auth/register_email.html` - Registration page
- `app/templates/auth/verify_otp.html` - OTP verification page
- `app/templates/auth/login_email.html` - Login page
- `app/templates/auth/forgot_password.html` - Password reset request
- `app/templates/auth/reset_password.html` - Password reset form

### Configuration
- `config/config.py` - Updated with email and JWT settings
- `.env.example` - Example environment variables

### Documentation
- `AUTH_IMPLEMENTATION.md` - Complete technical documentation
- `AUTH_QUICKSTART.md` - This file

## Architecture

```
Authentication System
├── Controllers (auth_email_controller.py)
│   ├── /auth/register - Entry point
│   ├── /auth/verify-otp - OTP verification
│   ├── /auth/login - User login
│   └── /auth/forgot-password - Password reset
│
├── Services (auth_service.py)
│   ├── request_registration() - Send OTP
│   ├── verify_otp_and_register() - Create account
│   ├── login() - Authenticate user
│   └── reset_password() - Password reset
│
├── Repositories
│   ├── UserRepository - User CRUD
│   └── OTPRepository - OTP CRUD
│
├── Models
│   ├── User - User account
│   └── OTP - One-time passwords
│
└── Utilities
    ├── auth_utils.py - Hash/verify passwords & OTPs
    └── email_utils.py - Send emails
```

## Security Summary

✓ Passwords: Bcrypt hashing (rounds=12)  
✓ OTPs: Bcrypt hashed, 7-minute expiry  
✓ Email: TLS encryption, credentials in env  
✓ Sessions: HttpOnly, SameSite cookies  
✓ Validation: Password strength enforcement  

## Next Steps

1. **Email Configuration**: Set up your email provider (see Step 2 above)
2. **Test Flows**: Try registration, login, and password reset
3. **Customize**: Modify templates to match your branding
4. **Deploy**: Set environment variables securely in production

## Troubleshooting

**OTP Not Sending?**
- Check `.env` email credentials
- Verify MAIL_SERVER and MAIL_PORT
- Check console/logs for errors

**Registration Failing?**
- Verify password meets requirements (8+ chars, uppercase, lowercase, number, special char)
- Check database table exists: `SELECT * FROM otps;`

**Login Not Working?**
- Verify user exists: `SELECT * FROM users WHERE email='...';`
- Check password hashing

## Support Files

- **Complete Documentation**: `AUTH_IMPLEMENTATION.md`
- **Example `.env`**: `.env.example`
- **Code Examples**: Included in this guide


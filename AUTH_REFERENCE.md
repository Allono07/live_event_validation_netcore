# Authentication Module - Quick Reference

## Setup (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure email (.env file)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=app-password

# 3. Start app (creates DB tables automatically)
python3 ./run.py
```

## Web Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/auth/register` | GET/POST | Email registration |
| `/auth/verify-otp` | GET/POST | Verify OTP & set password |
| `/auth/login` | GET/POST | Login with email & password |
| `/auth/forgot-password` | GET/POST | Request password reset |
| `/auth/reset-password` | GET/POST | Reset password with OTP |
| `/auth/logout` | POST | Logout user |

## API Endpoints

### Registration (2 steps)

**Step 1: Send OTP**
```
POST /auth/api/register
{
    "email": "user@example.com"
}
```

**Step 2: Verify & Create Account**
```
POST /auth/api/verify-otp
{
    "email": "user@example.com",
    "otp": "123456",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "username": "john_doe" (optional)
}
```

### Login

```
POST /auth/api/login
{
    "email": "user@example.com",
    "password": "SecurePass123!"
}
```

### Password Reset (2 steps)

**Step 1: Request Reset**
```
POST /auth/api/forgot-password
{
    "email": "user@example.com"
}
```

**Step 2: Reset Password**
```
POST /auth/api/reset-password
{
    "email": "user@example.com",
    "otp": "654321",
    "password": "NewSecurePass123!",
    "password_confirm": "NewSecurePass123!"
}
```

## Code Usage

### In Your Application

```python
from app.services.auth_service import AuthService

auth = AuthService()

# Request registration (sends OTP)
success, msg = auth.request_registration('user@example.com')

# Verify OTP and create account
success, msg = auth.verify_otp_and_register(
    email='user@example.com',
    otp='123456',
    password='SecurePass123!',
    password_confirm='SecurePass123!'
)

# Login
success, msg, user_data = auth.login('user@example.com', 'SecurePass123!')

# Password reset
success, msg = auth.request_password_reset('user@example.com')
success, msg = auth.reset_password(
    email='user@example.com',
    otp='654321',
    new_password='NewSecurePass123!',
    password_confirm='NewSecurePass123!'
)
```

### Password/OTP Utilities

```python
from app.utils.auth_utils import (
    generate_otp,
    hash_password,
    verify_password,
    is_strong_password,
    hash_otp,
    verify_otp
)

# Generate 6-digit OTP
otp = generate_otp()  # '123456'

# Hash password
pwd_hash = hash_password('MyPassword123!')
verify_password('MyPassword123!', pwd_hash)  # True

# Validate password strength
is_strong, msg = is_strong_password('weak')
# is_strong = False, msg = "Password must be at least 8 characters..."

# OTP hashing
otp_hash = hash_otp('123456')
verify_otp('123456', otp_hash)  # True
```

### Send Emails

```python
from app.utils.email_utils import (
    send_otp_email,
    send_welcome_email,
    send_password_reset_email
)

send_otp_email('user@example.com', '123456')
send_welcome_email('user@example.com', 'john_doe')
send_password_reset_email('user@example.com', '654321')
```

## Models

### OTP Model
```python
from app.models.otp import OTP

otp = OTP(
    email='user@example.com',
    otp_hash='$2b$12$...',  # bcrypt hash
    expires_at=datetime.utcnow() + timedelta(minutes=7),
    is_used=False
)

# Methods
otp.is_valid()      # Check if valid (not expired, not used)
otp.is_expired()    # Check if expired
```

### User Model
```python
from app.models.user import User

user = User(
    email='user@example.com',
    username='john_doe',
    password='$2b$12$...',  # bcrypt hash
    is_active=True
)

user.to_dict()  # {'id': 1, 'email': '...', 'username': '...', ...}
```

## Database Queries

```python
from app.models.user import User
from app.models.otp import OTP

# Find user
user = User.query.filter_by(email='user@example.com').first()

# Find valid OTP
otp = OTP.query.filter_by(email='user@example.com').first()
if otp and otp.is_valid():
    # Use OTP
    pass

# Count users
user_count = User.query.count()

# Get all active users
active_users = User.query.filter_by(is_active=True).all()
```

## Password Requirements

✓ 8+ characters  
✓ Uppercase letter (A-Z)  
✓ Lowercase letter (a-z)  
✓ Digit (0-9)  
✓ Special char (!@#$%^&*)  

**Valid**: `SecurePass123!`  
**Invalid**: `password123`, `Pass`, `PASSWORD123`

## OTP Lifecycle

1. **Generate**: `generate_otp()` → `123456`
2. **Hash**: `hash_otp('123456')` → `$2b$12$...`
3. **Store**: Save hash in DB (not plain OTP)
4. **Verify**: `verify_otp('123456', hash)` → True/False
5. **Expire**: Auto-expires after 7 minutes
6. **Use Once**: Marked as used after verification

## Security Features

- ✓ **Passwords**: Bcrypt (12 rounds)
- ✓ **OTPs**: Bcrypt hashed, 7-min expiry
- ✓ **Email**: TLS encryption
- ✓ **Sessions**: HttpOnly, SameSite cookies
- ✓ **Validation**: Strong password checks

## Error Responses

### 400 Bad Request
```json
{
    "success": false,
    "message": "Password must be at least 8 characters long"
}
```

### 401 Unauthorized
```json
{
    "success": false,
    "message": "Invalid email or password"
}
```

### 409 Conflict
```json
{
    "success": false,
    "message": "Email already registered"
}
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| OTP not sending | Check email config in `.env` |
| Password too weak | Use SecurePass123! format |
| OTP expired | 7-minute window, request new |
| User not found | Check email spelling |
| Login fails | Verify email & password match |

## Files Structure

```
app/
├── models/
│   └── otp.py                      # OTP model
├── repositories/
│   └── otp_repository.py           # OTP data access
├── services/
│   └── auth_service.py             # Auth business logic
├── utils/
│   ├── auth_utils.py               # Password/OTP utilities
│   └── email_utils.py              # Email sending
├── controllers/
│   └── auth_email_controller.py    # Routes
└── templates/auth/
    ├── register_email.html         # Register page
    ├── verify_otp.html             # OTP verification
    ├── login_email.html            # Login page
    ├── forgot_password.html        # Password reset request
    └── reset_password.html         # Password reset form

config/
└── config.py                       # Email & JWT settings

Documentation/
├── AUTH_IMPLEMENTATION.md          # Complete guide
├── AUTH_QUICKSTART.md              # Setup guide
├── AUTHENTICATION_COMPLETE.md      # Summary
└── AUTH_REFERENCE.md               # This file
```

## Gmail Setup

1. Enable 2-Factor Authentication
2. Go to https://myaccount.google.com/apppasswords
3. Select Mail → Windows Computer
4. Copy 16-char password to `MAIL_PASSWORD` in `.env`

## Testing

```bash
# Test all imports
python3 -c "from app import create_app; app = create_app(); print('✓ OK')"

# Test auth utilities
python3 -c "
from app.utils.auth_utils import generate_otp, hash_password
otp = generate_otp()
pwd = hash_password('SecurePass123!')
print(f'OTP: {otp}, Password hashed: OK')
"

# Test registration flow
curl -X POST http://localhost:5001/auth/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

## Next Steps

1. ✓ Install dependencies
2. ✓ Configure email (.env)
3. ✓ Start application
4. ✓ Test registration at `/auth/register`
5. ✓ Customize templates
6. ✓ Deploy

See `AUTH_QUICKSTART.md` for detailed setup.


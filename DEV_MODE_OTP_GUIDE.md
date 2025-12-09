# Development Mode - OTP Logging Guide

## Overview

In development mode, OTPs are **logged to the console** instead of being sent via email. This allows you to quickly test the registration and password reset flows without configuring email.

## How It Works

When running in development mode (`FLASK_ENV=development` or `debug=True`):

1. **Registration Flow**:
   ```
   User enters email → OTP generated → OTP logged to console
   
   Console output:
   🔐 DEV MODE - OTP for user@example.com: 654321
   ```

2. **Password Reset Flow**:
   ```
   User requests reset → OTP generated → OTP logged to console
   
   Console output:
   🔐 DEV MODE - Password Reset OTP for user@example.com: 123456
   ```

## Testing the Flow

### Step 1: Start the Flask App
```bash
python3 ./run.py
```

You'll see logs like:
```
2025-12-09 21:50:00,000 - werkzeug - INFO - Running on http://127.0.0.1:5001
...
```

### Step 2: Start Registration
1. Open http://localhost:5001/auth/register
2. Enter email: `test@example.com`
3. Click "Send Verification Code"

### Step 3: Check Console for OTP
In your terminal, you'll see:
```
WARNING - 🔐 DEV MODE - OTP for test@example.com: 654321
```

### Step 4: Use OTP in Form
1. You'll be redirected to `/auth/verify-otp`
2. Enter the OTP you saw in the console: `654321`
3. Create a strong password
4. Click "Verify & Register"

### Step 5: Login
1. Go to `/auth/login`
2. Enter your email and password
3. You're logged in!

## Password Reset Testing

### Step 1: Go to Forgot Password
1. Click "Forgot your password?" on login page
2. Enter your registered email

### Step 2: Check Console for Reset OTP
```
WARNING - 🔐 DEV MODE - Password Reset OTP for test@example.com: 123456
```

### Step 3: Use Reset OTP
1. Enter the OTP from console
2. Create new password
3. Click "Reset Password"

### Step 4: Login with New Password
1. Go back to login
2. Use your email and new password

## Console Log Format

All OTP logs follow this pattern:
```
[LEVEL] - 🔐 DEV MODE - [MESSAGE]: [OTP]
```

Examples:
```
WARNING - 🔐 DEV MODE - OTP for john@example.com: 543210
WARNING - 🔐 DEV MODE - Password Reset OTP for jane@example.com: 987654
```

## Switching to Production Email Mode

When you're ready to enable real email sending:

### Option 1: Change Environment Variable
```bash
export FLASK_ENV=production
python3 ./run.py
```

### Option 2: Configure Email in config.py
```python
# config/config.py
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'your-email@gmail.com'
MAIL_PASSWORD = 'app-specific-password'
```

Then emails will be sent instead of logged.

## Code Changes

### Modified Files

**app/utils/email_utils.py**:
```python
def send_otp_email(email: str, otp: str) -> bool:
    # In development mode, log OTP instead of sending email
    is_dev = current_app.config.get('ENV') == 'development' or current_app.debug
    
    if is_dev:
        current_app.logger.warning(f"🔐 DEV MODE - OTP for {email}: {otp}")
        return True
    
    # ... production email sending code ...
```

Same logic applied to `send_password_reset_email()`.

## Debugging Tips

### Finding OTPs in Logs

If you have a long terminal output, search for the emoji:
```bash
# On macOS/Linux
grep "🔐" /path/to/terminal/output.log
```

### Terminal Search
Many terminals have a search feature (Cmd+F on Mac):
- Press Cmd+F in terminal
- Search for: `🔐` or `DEV MODE`

### Python Logging
You can also modify the log level to make DEV messages more prominent:

In `app/__init__.py`:
```python
import logging
logging.getLogger().setLevel(logging.WARNING)
```

## Testing Checklist

- [ ] Start Flask app (`python3 ./run.py`)
- [ ] Visit `/auth/register`
- [ ] Enter test email
- [ ] See OTP in console with 🔐 emoji
- [ ] Copy OTP from console
- [ ] Verify OTP in form
- [ ] Complete registration
- [ ] Login with credentials
- [ ] Test password reset flow
- [ ] Verify reset OTP in console
- [ ] Complete password reset
- [ ] Login with new password

## Common Issues

**Q: I don't see the OTP log**
A: Make sure your terminal is showing all output. The log level might be set too high. Check that the app is running in development mode.

**Q: The OTP is expired before I can use it**
A: OTPs are valid for 7 minutes. Work quickly! In dev mode, you have time.

**Q: I see "Failed to send email" in production**
A: Check your email configuration in `config/config.py`. Make sure SMTP credentials are correct.

**Q: How do I know which OTP is for which request?**
A: The log shows the email address: `OTP for user@example.com: 123456`. Match the email to know which one is yours.

## Next Steps

1. **Test the complete flow** using the checklist above
2. **When ready for production**, configure real email (Gmail, SendGrid, etc.)
3. **Update environment** to `FLASK_ENV=production`
4. **Deploy** to production server


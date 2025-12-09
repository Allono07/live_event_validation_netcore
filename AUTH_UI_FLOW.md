# Authentication UI Flow - Visual Guide

## Navigation Map

```
┌─────────────────────────────────────────────────────────────┐
│                    LIVE VALIDATION DASHBOARD                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   USER VISITS ANY PAGE       │
        │   (Unauthenticated)          │
        └──────────────────┬───────────┘
                           │
                 ┌─────────▼─────────┐
                 │ REDIRECT TO LOGIN │
                 └─────────┬─────────┘
                           │
         ┌─────────────────▼────────────────────┐
         │  /auth/login                         │
         │  (Email-based Login Screen)          │
         │                                      │
         │  ┌────────────────────────────────┐ │
         │  │ Email:      [__________]       │ │
         │  │ Password:   [__________]       │ │
         │  │ ☐ Remember me                  │ │
         │  │ [    Login Button    ]          │ │
         │  └────────────────────────────────┘ │
         │                                      │
         │  Don't have account? → Register     │
         │  Forgot password? → Reset Password  │
         └──────────────────────────────────┘
                  ▲              │
         YES │    │              │ NO / INVALID
             │    │              ▼
        ┌────┴────▼───────────────────────┐
        │ AUTHENTICATE USER               │
        │ (Email + Password Check)        │
        │                                 │
        │ ✓ Email exists                 │
        │ ✓ Password matches             │
        └────┬───────────────────────────┘
             │
             ▼
    ┌─────────────────────┐
    │ LOGIN SUCCESSFUL    │
    └─────────┬───────────┘
              │
              ▼
    ┌─────────────────────┐
    │ SET SESSION COOKIE  │
    │ (Remember me option)│
    └─────────┬───────────┘
              │
              ▼
    ┌────────────────────────────┐
    │ REDIRECT TO DASHBOARD      │
    │ /dashboard (/)             │
    │                            │
    │ ✓ View applications       │
    │ ✓ Manage validation rules │
    │ ✓ View live events        │
    └────────┬───────────────────┘
             │
             ▼
    ┌─────────────────────────┐
    │  USER CLICKS LOGOUT     │
    └──────────┬──────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ DESTROY SESSION COOKIE   │
    │ LOG OUT USER             │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ REDIRECT TO LOGIN PAGE   │
    │ /auth/login              │
    └──────────────────────────┘
```

---

## Registration Flow

```
FIRST-TIME USER REGISTRATION
════════════════════════════

   ┌─────────────────────────┐
   │ Click "Register here"   │
   │ from Login page         │
   └────────┬────────────────┘
            │
            ▼
   ┌────────────────────────────────┐
   │ /auth/register                 │
   │ (Email Entry Page)             │
   │                                │
   │ ┌───────────────────────────┐ │
   │ │ Email: [user@example.com] │ │
   │ │                           │ │
   │ │ [Send Verification Code] │ │
   │ └───────────────────────────┘ │
   │                                │
   │ "Already have account?"        │
   │ → Back to Login                │
   └────────┬─────────────────────┘
            │
            ▼
   ┌─────────────────────────┐
   │ VALIDATE EMAIL          │
   │ CHECK IF REGISTERED     │
   └────────┬────────────────┘
            │
   ┌────────┴────────┐
   │                 │
   YES (exists) ─────┤  NO (new)
   ▼                 │  ▼
ERROR: Already   GENERATE OTP
Registered       SEND EMAIL
   │              │
   └─────┬────────┘
         │
         ▼
   ┌────────────────────────────────┐
   │ /auth/verify-otp?email=...     │
   │ (OTP + Password Setup Page)    │
   │                                │
   │ ┌───────────────────────────┐ │
   │ │ OTP Code: [1 2 3 4 5 6]  │ │
   │ │ Username: [optional]      │ │
   │ │ Password: [________]      │ │
   │ │   ✓ 8+ characters        │ │
   │ │   ✓ Uppercase            │ │
   │ │   ✓ Lowercase            │ │
   │ │   ✓ Digit                │ │
   │ │   ✓ Special char         │ │
   │ │ Confirm: [________]      │ │
   │ │ [   Verify & Register  ] │ │
   │ └───────────────────────────┘ │
   │                                │
   │ "Already have account?"        │
   │ → Back to Login                │
   └────────┬─────────────────────┘
            │
            ▼
   ┌──────────────────────────────┐
   │ VALIDATE:                    │
   │ ✓ OTP valid & not expired   │
   │ ✓ Password meets criteria   │
   │ ✓ Passwords match           │
   └────────┬─────────────────────┘
            │
   ┌────────┴─────────┐
   NO │                │ YES
   ▼  │                ▼
ERROR  │           CREATE USER
   │   │           IN DATABASE
   └─┬─┘               │
     │                 ▼
     └────────┬────────┘
              │
              ▼
   ┌────────────────────────────┐
   │ REGISTRATION SUCCESS       │
   │ Account created!           │
   └────────┬───────────────────┘
            │
            ▼
   ┌────────────────────────────┐
   │ REDIRECT TO LOGIN          │
   │ /auth/login                │
   │                            │
   │ "You can now login"        │
   └────────────────────────────┘
```

---

## Password Reset Flow

```
FORGOT PASSWORD RECOVERY
═════════════════════════

   ┌──────────────────────────────┐
   │ Click "Forgot your password?"│
   │ from Login page              │
   └────────┬─────────────────────┘
            │
            ▼
   ┌────────────────────────────────┐
   │ /auth/forgot-password          │
   │ (Email Entry Page)             │
   │                                │
   │ ┌───────────────────────────┐ │
   │ │ Email: [user@example.com] │ │
   │ │                           │ │
   │ │ [Send Reset Code]        │ │
   │ └───────────────────────────┘ │
   └────────┬─────────────────────┘
            │
            ▼
   ┌────────────────────────────┐
   │ FIND USER BY EMAIL         │
   │ GENERATE RESET OTP         │
   │ SEND EMAIL WITH CODE       │
   └────────┬───────────────────┘
            │
            ▼
   ┌────────────────────────────────┐
   │ /auth/reset-password?email=... │
   │ (OTP + New Password Page)      │
   │                                │
   │ ┌───────────────────────────┐ │
   │ │ Reset Code: [1 2 3 4 5 6]│ │
   │ │ New Password: [_______]  │ │
   │ │   ✓ 8+ characters        │ │
   │ │   ✓ Uppercase            │ │
   │ │   ✓ Lowercase            │ │
   │ │   ✓ Digit                │ │
   │ │   ✓ Special char         │ │
   │ │ Confirm: [_______]       │ │
   │ │ [    Reset Password    ] │ │
   │ └───────────────────────────┘ │
   └────────┬──────────────────────┘
            │
            ▼
   ┌────────────────────────────┐
   │ VALIDATE:                  │
   │ ✓ OTP valid & not expired │
   │ ✓ OTP not already used    │
   │ ✓ Password meets criteria │
   │ ✓ Passwords match         │
   └────────┬──────────────────┘
            │
   ┌────────┴──────────┐
   NO │                 │ YES
   ▼  │                 ▼
ERROR  │          UPDATE PASSWORD
   │   │          IN DATABASE
   └─┬─┘               │
     │                 ▼
     └────────┬────────┘
              │
              ▼
   ┌───────────────────────────────┐
   │ PASSWORD RESET SUCCESS        │
   │ Your password has been reset! │
   └────────┬──────────────────────┘
            │
            ▼
   ┌──────────────────────────┐
   │ REDIRECT TO LOGIN        │
   │ /auth/login              │
   │                          │
   │ "Sign in with new pwd"   │
   └──────────────────────────┘
```

---

## Route Summary

| Page | Route | Method | Purpose |
|------|-------|--------|---------|
| **Login** | `/auth/login` | GET/POST | Email + Password authentication |
| **Register** | `/auth/register` | GET/POST | Start new account registration |
| **Verify OTP** | `/auth/verify-otp` | GET/POST | Complete registration with OTP |
| **Forgot PW** | `/auth/forgot-password` | GET/POST | Request password reset |
| **Reset PW** | `/auth/reset-password` | GET/POST | Complete password reset |
| **Logout** | `/auth/logout` | POST | End user session |
| **Dashboard** | `/` | GET | Main application (requires auth) |

---

## Key Changes from Old UI

### ❌ Removed
- Username field (replaced with email)
- "username == password" validation message
- Manual username/password matching

### ✅ Added
- Email-based authentication
- Email verification with OTP
- Password strength validation (8+, uppercase, lowercase, digit, special char)
- Password reset functionality
- "Remember me" option
- Account registration flow
- Proper password hashing (bcrypt)
- OTP expiration (7 minutes)
- One-time OTP use

---

## Security Improvements

| Feature | Before | After |
|---------|--------|-------|
| **Password Storage** | Plaintext | Bcrypt (12 rounds) |
| **Password Rules** | None | 8+, uppercase, lower, digit, special |
| **Email Verification** | None | 6-digit OTP |
| **OTP Storage** | N/A | Bcrypt hashed |
| **OTP Expiry** | N/A | 7 minutes |
| **Password Recovery** | None | Email-based OTP flow |
| **Session Security** | Basic | HttpOnly, SameSite cookies |


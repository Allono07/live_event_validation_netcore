# Live Validation Dashboard - Usage Guide

## 🚀 Getting Started

### 1. Start the Application
```bash
cd /Users/allen.thomson/Desktop/sampleapp/automation/live_validation_dashboard
PORT=5001 /usr/local/bin/python3 run.py
```

Access the application at: **http://127.0.0.1:5001**

---

## 📝 Creating Your First App

### Step 1: Login
- Username: Any value (e.g., `admin`)
- Password: Same as username (e.g., `admin`)
- *Note: This is prototype authentication where username == password*

### Step 2: Create an Application
1. Click **"+ Create New App"** button
2. Fill in the form:
   - **App Name**: Name of your application (e.g., "My Mobile App")
   - **App ID** (Optional): 
     - You can paste a custom App ID (e.g., `my-app-123`)
     - Or leave empty to auto-generate a unique ID
   - **Description**: Optional description
3. Click **"Create"**

### Step 3: Upload Validation Rules

#### CSV Format
Your CSV file must have exactly 3 columns with **event names appearing only once**:

```csv
eventName,eventPayload,dataType
user_login,user_id,integer
,timestamp,date
,device_type,text
```

**Important:** Event names are written only in the first row of each event, then left empty for subsequent fields of the same event.

**Columns:**
- `eventName`: Name of the event (e.g., `user_login`) - **write only once per event**
- `eventPayload`: Field name in the event payload (e.g., `user_id`)
- `dataType`: Data type - one of: `text`, `date`, `integer`, `float`, `boolean`

**Example CSV:**
```csv
eventName,eventPayload,dataType
user_login,user_id,integer
,timestamp,date
,device_type,text
user_signup,email,text
,age,integer
,registration_date,date
purchase_completed,amount,float
,product_id,integer
,transaction_date,date
```

A sample file is provided: `sample_validation_rules.csv`

#### Upload Steps:
1. Click on your app to view details
2. Click **"Upload CSV Rules"** button
3. Select your CSV file
4. Click **"Upload"**

---

## 🔌 API Integration

### Endpoint Format
```
POST http://127.0.0.1:5001/api/logs/{app_id}
```

Replace `{app_id}` with your application's App ID (visible on the app detail page)

### Request Format
Send a JSON payload with this structure:

```json
{
  "event_name": "user_login",
  "payload": {
    "user_id": 123,
    "timestamp": "2025-11-03 10:30:00",
    "device_type": "iOS"
  }
}
```

### Example with cURL
```bash
curl -X POST http://127.0.0.1:5001/api/logs/YOUR_APP_ID \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "user_login",
    "payload": {
      "user_id": 123,
      "timestamp": "2025-11-03 10:30:00",
      "device_type": "iOS"
    }
  }'
```

### Example Response (Success)
```json
{
  "id": 1,
  "app_id": "YOUR_APP_ID",
  "event_name": "user_login",
  "is_valid": true,
  "validation_message": "Validation passed",
  "timestamp": "2025-11-03T10:30:00"
}
```

### Example Response (Validation Failed)
```json
{
  "id": 2,
  "app_id": "YOUR_APP_ID",
  "event_name": "user_login",
  "is_valid": false,
  "validation_message": "Field 'user_id': Expected integer, got string",
  "timestamp": "2025-11-03T10:30:00"
}
```

---

## 📊 Live Monitoring

### Real-time Dashboard Features

When viewing an app detail page:

1. **Stats Cards** (Auto-updating):
   - Total Logs: All logs received
   - Passed: Successfully validated logs
   - Failed: Validation failures
   - Success Rate: Percentage of passed logs

2. **Live Logs Table**:
   - Shows logs as they arrive in real-time
   - Color-coded: Green (passed) / Red (failed)
   - Displays timestamp, event name, status, and validation message
   - Keeps last 50 logs

3. **WebSocket Connection**:
   - Green badge: Connected
   - Red badge: Disconnected
   - Auto-reconnects if connection drops

---

## � API Request Logging

All incoming API requests are automatically logged to `api_logs.log` in the project root directory.

**Log Format:**
```
2025-11-03 12:00:00 - app.controllers.api_controller - INFO - === INCOMING LOG REQUEST ===
2025-11-03 12:00:00 - app.controllers.api_controller - INFO - App ID: your-app-id
2025-11-03 12:00:00 - app.controllers.api_controller - INFO - IP Address: 127.0.0.1
2025-11-03 12:00:00 - app.controllers.api_controller - INFO - Request Data: {'event_name': 'user_login', 'payload': {...}}
2025-11-03 12:00:00 - app.controllers.api_controller - INFO - Validation PASSED
```

**To view logs:**
```bash
# View latest logs
tail -f api_logs.log

# View all logs
cat api_logs.log

# Search for specific app
grep "App ID: your-app-id" api_logs.log
```

---

## �🔍 Data Types Validation

The system validates the following data types:

### 1. **text**
- Accepts: Any string value
- Example: `"hello"`, `"user@example.com"`

### 2. **integer**
- Accepts: Whole numbers
- Example: `123`, `-45`, `0`
- Rejects: `"123"` (string), `12.5` (float)

### 3. **float**
- Accepts: Decimal numbers
- Example: `12.5`, `99.99`, `-0.5`
- Rejects: `"12.5"` (string)

### 4. **date**
- Accepts: Date strings in format `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD`
- Example: `"2025-11-03 10:30:00"`, `"2025-11-03"`
- Rejects: Invalid dates, wrong format

### 5. **boolean**
- Accepts: `true`, `false` (case-insensitive)
- Example: `true`, `false`, `True`, `FALSE`
- Rejects: `1`, `0`, `"yes"`, `"no"`

---

## 🛠️ Troubleshooting

### Issue: Port 5000 already in use
**Solution**: Use a different port
```bash
PORT=5001 /usr/local/bin/python3 run.py
```

### Issue: CSV upload fails
**Solution**: Check your CSV format:
- Must have header row: `eventName,eventPayload,dataType`
- No extra columns
- Valid data types only

### Issue: Validation always fails
**Solution**: 
- Check data types match between CSV and actual payload
- Ensure field names match exactly (case-sensitive)
- Verify date format is correct

### Issue: Live updates not working
**Solution**:
- Check WebSocket connection status badge
- Refresh the page
- Check browser console for errors

---

## 📁 Project Structure

```
live_validation_dashboard/
├── app/
│   ├── controllers/      # HTTP & WebSocket endpoints
│   ├── models/           # Database models
│   ├── repositories/     # Data access layer
│   ├── services/         # Business logic
│   ├── validators/       # Validation logic
│   ├── templates/        # HTML templates
│   └── static/           # CSS, JavaScript
├── config/               # Configuration
├── instance/             # Database file
├── sample_validation_rules.csv  # Example CSV
└── run.py               # Application entry point
```

---

## 🔐 Security Notes (Production)

⚠️ **Current authentication is for PROTOTYPE only**

For production deployment:
1. Replace username==password authentication with proper auth
2. Use HTTPS (set `SESSION_COOKIE_SECURE = True`)
3. Change `SECRET_KEY` to a strong random value
4. Use a production database (PostgreSQL, MySQL)
5. Use a production WSGI server (Gunicorn, uWSGI)
6. Add rate limiting for API endpoints
7. Add API key authentication for mobile apps

---

## 📞 Support

For issues or questions, refer to the main README.md file.

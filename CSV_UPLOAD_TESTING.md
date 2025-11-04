# CSV Upload Testing Guide

## ✅ What's Been Fixed

### 1. CSV Parser (VERIFIED WORKING)
The CSV parser correctly handles the **merged event name format** where the event name appears only once:

```csv
eventName,eventPayload,dataType
regular_app_launched,eventId,integer
,networkMode,text
,sessionId,text
```

**Test Results:**
- ✅ Reads event name once from first row
- ✅ Applies event name to all subsequent rows with empty eventName
- ✅ Switches to new event when eventName appears again
- ✅ Tested with 3 events, 18 fields - all parsed correctly

### 2. Upload Flow (JUST FIXED)
All error handling and success paths now properly redirect back to the app detail page:

**Changes Made:**
- ✅ Access denied → Flash message + redirect to dashboard
- ✅ No file uploaded → Flash message + redirect to app detail
- ✅ No file selected → Flash message + redirect to app detail
- ✅ Invalid file type → Flash message + redirect to app detail
- ✅ Success upload → Flash message + redirect to app detail
- ✅ Error during upload → Flash message + redirect to app detail

**Before:** User stuck on `/upload` URL after CSV upload
**After:** User stays on app detail page with flash notification

## 🧪 How to Test

### Step 1: Start the Application
```bash
cd /Users/allen.thomson/Desktop/sampleapp/automation/live_validation_dashboard
python3 run.py
```

### Step 2: Login
- URL: http://localhost:5001
- Username: `admin`
- Password: `admin`

### Step 3: Create App
1. Click "Add New App" button
2. Enter App Name: "Test App"
3. Manually enter App ID: "test-app-001"
4. Click "Create App"

### Step 4: Upload CSV
1. Click on your new app card
2. In the "Validation Rules" section, click "Choose File"
3. Upload `sample_validation_rules.csv`
4. Click "Upload Rules"

**Expected Behavior:**
- ✅ Page stays on app detail (URL: `/app/test-app-001`)
- ✅ Green flash message: "Validation rules uploaded: X rules"
- ✅ Rules appear in the table below

### Step 5: Verify Rules Display
Check the validation rules table shows:
```
Event Name              | Field Name           | Data Type
---------------------------------------------------------
regular_app_launched    | eventId              | integer
regular_app_launched    | networkMode          | text
regular_app_launched    | sessionId            | text
regular_app_launched    | identity             | text
regular_app_launched    | eventTime            | text
regular_app_launched    | screenOrientation    | text
regular_app_launched    | timeZone             | text
user_logged_in          | eventId              | integer
user_logged_in          | networkMode          | text
user_logged_in          | sessionId            | text
user_logged_in          | identity             | text
user_logged_in          | eventTime            | text
inbox_clicked           | eventId              | integer
inbox_clicked           | trid                 | text
inbox_clicked           | inboxClickLink       | text
inbox_clicked           | sessionId            | text
inbox_clicked           | identity             | text
inbox_clicked           | eventTime            | text
```

## 📝 Sample CSV Format

Your CSV should look like this (event name appears once, then empty cells):

```csv
eventName,eventPayload,dataType
regular_app_launched,eventId,integer
,networkMode,text
,sessionId,text
,identity,text
,eventTime,text
,screenOrientation,text
,timeZone,text
user_logged_in,eventId,integer
,networkMode,text
,sessionId,text
,identity,text
,eventTime,text
inbox_clicked,eventId,integer
,trid,text
,inboxClickLink,text
,sessionId,text
,identity,text
,eventTime,text
```

## 🚨 Error Scenarios to Test

### Test 1: No File Selected
1. Click "Choose File" but don't select anything
2. Click "Upload Rules"
3. **Expected:** Flash message "No file selected" + stay on app detail page

### Test 2: Wrong File Type
1. Upload a `.txt` or `.xlsx` file
2. **Expected:** Flash message "File must be CSV" + stay on app detail page

### Test 3: Invalid CSV Format
Create a CSV with wrong headers:
```csv
event,payload,type
user_login,user_id,integer
```
3. **Expected:** Flash message with error + stay on app detail page

## 🔍 Debugging

### Check Application Logs
```bash
tail -f /Users/allen.thomson/Desktop/sampleapp/automation/live_validation_dashboard/logs/app.log
```

### Check Database
```bash
cd /Users/allen.thomson/Desktop/sampleapp/automation/live_validation_dashboard
python3 << 'EOF'
from app import create_app
from app.models import ValidationRule
from app.extensions import db

app = create_app()
with app.app_context():
    rules = ValidationRule.query.all()
    for rule in rules:
        print(f"{rule.event_name:30} | {rule.field_name:20} | {rule.data_type}")
    print(f"\nTotal rules in database: {len(rules)}")
EOF
```

### Test CSV Parser Directly
```bash
cd /Users/allen.thomson/Desktop/sampleapp/automation/live_validation_dashboard
python3 << 'EOF'
from app.utils.csv_parser import parse_validation_rules

with open('sample_validation_rules.csv', 'r') as f:
    csv_content = f.read()

rules = parse_validation_rules(csv_content)
for rule in rules:
    print(f"{rule['event_name']:30} | {rule['field_name']:20} | {rule['data_type']}")
print(f"\nTotal parsed: {len(rules)}")
EOF
```

## ✨ Next Steps

After verifying CSV upload works:

1. **Test Live Validation:**
   - Send test logs via API
   - Watch them appear in real-time on app detail page

2. **Test with Real Mobile App:**
   - Use ngrok to expose local server
   - Configure mobile app to send logs
   - Verify validation works correctly

3. **Production Preparation:**
   - Review security settings
   - Set up environment variables
   - Configure production database
   - Set up proper logging

## 📚 Related Files

- **CSV Parser:** `app/utils/csv_parser.py`
- **Upload Controller:** `app/controllers/dashboard_controller.py` (lines 85-115)
- **Service Layer:** `app/services/validation_service.py`
- **Template:** `app/templates/app_detail.html`
- **Sample CSV:** `sample_validation_rules.csv`

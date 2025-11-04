# Quick Start Guide - Updated Application

## 🚀 Start the Application

```bash
cd /Users/allen.thomson/Desktop/sampleapp/automation/live_validation_dashboard
python3 run.py
```

The application will start on: **http://localhost:5001**

## 📝 What's New

### 1. CSV Format Change
Your CSV files now need **5 columns** instead of 3:
```csv
eventName,eventPayload,dataType,Required,PatternRange
```

### 2. Event Filtering
- **User Events** (eventId = 0): Validated and shown in "User Events" tab
- **System Events** (eventId ≠ 0): Not validated, shown in "System Events" tab

### 3. Timestamp Formatting
Unix timestamps like `1762151564369` are automatically formatted to readable dates.

## 🎯 Testing Steps

### Step 1: Login
- URL: http://localhost:5001
- Username: `admin`
- Password: `admin`

### Step 2: Create App
1. Click "Add New App"
2. Name: "My Test App"
3. App ID: "test-app-001"
4. Click "Create App"

### Step 3: Upload Validation Rules
1. Click on your app card
2. Click "Upload CSV Rules"
3. Select `sample_validation_rules.csv`
4. Click "Upload"
5. **Verify:** Rules table shows "Yes" or "No" in Required column

### Step 4: Send Test Events

**User Event (will be validated):**
```bash
curl -X POST http://localhost:5001/api/logs/test-app-001 \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": 0,
    "eventName": "regular_app_launched",
    "networkMode": "wifi",
    "sessionId": "session123",
    "identity": "user456",
    "eventTime": "1730646000000",
    "screenOrientation": "portrait",
    "timeZone": "UTC"
  }'
```

**System Event (will NOT be validated):**
```bash
curl -X POST http://localhost:5001/api/logs/test-app-001 \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": 5,
    "eventName": "system_heartbeat",
    "timestamp": "1730646000000"
  }'
```

### Step 5: Verify Results
1. Check "User Events" tab - should show validated event
2. Check "System Events" tab - should show system event
3. Verify timestamps are formatted (not showing as `1730646000000`)
4. Verify stats cards update

## 📊 Expected Results

### Validation Rules Table
```
Event Name              | Field Name        | Data Type | Required | Pattern/Range
regular_app_launched    | eventId           | integer   | Yes      | -
regular_app_launched    | networkMode       | text      | No       | -
regular_app_launched    | sessionId         | text      | Yes      | -
```

### User Events Tab
```
Timestamp               | Event Name             | Status  | Message
11/3/2025, 12:30:00 PM | regular_app_launched   | PASSED  | Validation completed
```

### System Events Tab
```
Timestamp               | Event Name        | Event ID | Details
11/3/2025, 12:30:05 PM | system_heartbeat  | 5        | System event (not validated)
```

## 🔍 Verification Checklist

- [ ] Application starts on port 5001
- [ ] Login works with admin/admin
- [ ] CSV upload accepts 5-column format
- [ ] Validation rules display Required as "Yes" or "No"
- [ ] Pattern/Range column shows "-" when empty
- [ ] User events (eventId=0) appear in User Events tab
- [ ] System events (eventId≠0) appear in System Events tab
- [ ] Unix timestamps are formatted correctly
- [ ] Tab counters update in real-time
- [ ] Stats cards show correct numbers

## 🐛 Troubleshooting

### CSV Upload Fails
- Check file has all 5 columns: eventName, eventPayload, dataType, Required, PatternRange
- Event name must appear in first row of each event

### Events Not Appearing
- Check eventId value in payload
- eventId must be exactly 0 (number) for user events
- Check browser console for errors

### Timestamps Show as Numbers
- Ensure timestamp is 13-digit Unix milliseconds
- Check browser console for JavaScript errors
- Verify app_detail.js loaded correctly

## 📞 Support

If issues persist:
1. Check browser console (F12)
2. Check `api_logs.log` file
3. Verify database initialized: `ls instance/logs.db`

## 🎉 You're All Set!

All requested features are now implemented:
- ✅ CSV format with Required and PatternRange
- ✅ Event filtering by eventId
- ✅ Separate tabs for user and system events
- ✅ Unix timestamp formatting
- ✅ Updated UI display

Start the app and test it out!

# Pagination Testing Guide

## Overview
I've created a SQL script (`insert_100_test_events.sql`) with 100 test records to verify pagination is working correctly.

## About the Test Data

The script inserts 100 log entries with:
- **App ID**: 1 (adjust if needed for your test app)
- **Event Names**: 11 different event types:
  - UserLogin (20 entries)
  - UserLogout (10 entries)
  - PageView (10 entries)
  - DataSync (10 entries)
  - ClickEvent (10 entries)
  - ProfileUpdate (7 entries)
  - FormSubmit (7 entries)
  - ErrorEvent (6 entries)
  - Other events

- **Validation Status**: Mix of Valid (85) and Invalid (15) entries
- **Timestamps**: Spread over ~100 minutes (newest first when ordered by created_at DESC)
- **Realistic Data**: JSON payloads match real event structures

## How to Use

### Option 1: MySQL Client (Recommended)

```bash
# Connect to your MySQL database
mysql -u val_user -p -h 127.0.0.1 validation_db < insert_100_test_events.sql
```

When prompted, enter password: `val_password` (or your configured password)

### Option 2: Copy-Paste in MySQL

1. Open MySQL client:
```bash
mysql -u val_user -p -h 127.0.0.1 validation_db
```

2. Paste entire SQL script content
3. Press Enter

### Option 3: Via Python Script

```python
import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1',
    user='val_user',
    password='val_password',
    database='validation_db'
)
cursor = conn.cursor()

with open('insert_100_test_events.sql', 'r') as f:
    sql = f.read()
    for statement in sql.split(';'):
        if statement.strip():
            cursor.execute(statement)

conn.commit()
cursor.close()
conn.close()
print("✅ 100 test records inserted successfully!")
```

## Testing Pagination

### Test 1: Verify Load More Button Appears

1. **Start Flask app**:
```bash
python3 run.py
```

2. **Login** to dashboard with test credentials

3. **Go to your test app detail page**

4. **Expected Results**:
   - Initial load shows first 50 events
   - "Load More" button appears below the table
   - Statistics show: Total Logs = 100

### Test 2: Click Load More Button

1. **Click the "Load more" button**
2. **Expected Results**:
   - Next 50 events load and append to table
   - "Load More" button disappears (all loaded)
   - No duplicate events

### Test 3: Verify Pagination API

Open browser console and run:

```javascript
// Test page 1
fetch('/app/YOUR_APP_ID/logs?page=1&limit=50')
    .then(r => r.json())
    .then(data => console.log('Page 1:', data));

// Test page 2
fetch('/app/YOUR_APP_ID/logs?page=2&limit=50')
    .then(r => r.json())
    .then(data => console.log('Page 2:', data));

// Verify response format
// Should return: {logs: [...], total: 100, page: 1, limit: 50}
```

Expected response:
```json
{
  "logs": [
    {
      "id": 1,
      "app_id": 1,
      "event_name": "UserLogin",
      "payload": "...",
      "validation_status": "Valid",
      "created_at": "2025-11-04T11:28:00",
      ...
    },
    // 49 more entries
  ],
  "total": 100,
  "page": 1,
  "limit": 50
}
```

### Test 4: Verify Event Coverage (With Fixed Calculation)

1. **Upload validation rules** if you haven't already
2. **Check Event Coverage section**
3. **Expected Results**:
   - Captured = distinct events from rules found in logs
   - Missing = distinct events in rules NOT found in logs
   - Total = total distinct events in rules
   - **Formula validates**: Captured + Missing = Total ✓

### Test 5: Check Different Limits

```javascript
// Test with different page sizes
fetch('/app/YOUR_APP_ID/logs?page=1&limit=10')
    .then(r => r.json())
    .then(data => console.log('Limit 10:', data));

fetch('/app/YOUR_APP_ID/logs?page=1&limit=25')
    .then(r => r.json())
    .then(data => console.log('Limit 25:', data));

fetch('/app/YOUR_APP_ID/logs?page=1&limit=100')
    .then(r => r.json())
    .then(data => console.log('Limit 100:', data));
```

## Cleanup

To remove test data later:

```sql
-- Delete all test records for app_id 1
DELETE FROM log_entries WHERE app_id = 1 AND created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR);

-- Or delete everything for app
DELETE FROM log_entries WHERE app_id = 1;
```

## Expected Pagination Behavior

### Page Size = 50 (Default)

| Page | Records | Range | Load More? |
|------|---------|-------|-----------|
| 1 | 50 | 1-50 | ✓ Yes |
| 2 | 50 | 51-100 | ✗ No (all loaded) |

### Page Size = 30

| Page | Records | Range | Load More? |
|------|---------|-------|-----------|
| 1 | 30 | 1-30 | ✓ Yes |
| 2 | 30 | 31-60 | ✓ Yes |
| 3 | 30 | 61-90 | ✓ Yes |
| 4 | 10 | 91-100 | ✗ No (all loaded) |

## Verification Checklist

- [ ] SQL script runs without errors
- [ ] MySQL shows 100 new records inserted: `SELECT COUNT(*) FROM log_entries;`
- [ ] Page loads without errors
- [ ] Initial load shows 50 records
- [ ] Load More button appears
- [ ] Clicking Load More appends next 50 records
- [ ] No duplicate records in table
- [ ] Statistics (Total, Passed, Failed) update correctly
- [ ] Filter dropdowns work with pagination
- [ ] Event Coverage calculation is correct (Captured + Missing = Total)

## Database Query to Verify Data

```sql
-- Count total test records
SELECT COUNT(*) as total FROM log_entries WHERE app_id = 1;

-- Check distribution by event name
SELECT event_name, COUNT(*) as count 
FROM log_entries 
WHERE app_id = 1 
GROUP BY event_name 
ORDER BY count DESC;

-- Check validation status distribution
SELECT validation_status, COUNT(*) as count 
FROM log_entries 
WHERE app_id = 1 
GROUP BY validation_status;

-- Verify ordering (should be newest first)
SELECT id, event_name, created_at 
FROM log_entries 
WHERE app_id = 1 
ORDER BY created_at DESC 
LIMIT 10;
```

## Troubleshooting

### "Load More" button doesn't appear

Check:
1. Logs endpoint returns correct total: `GET /app/{id}/logs?page=1&limit=1`
2. Response has `"total": 100` field
3. Browser console has no JavaScript errors
4. totalLogs variable is set: `console.log('totalLogs:', totalLogs)`

### Duplicate records in table

Check:
1. Pagination indices are correct
2. No overlapping page ranges
3. Records have unique IDs

### Pagination API returns empty

Check:
1. App ID is correct
2. Records are for app_id = 1 (or update query parameters)
3. Records aren't filtered by date range
4. User has access to app

---

**File Location**: `/Users/allen.thomson/Desktop/sampleapp/automation/live_validation_dashboard/insert_100_test_events.sql`

Ready to test! 🚀

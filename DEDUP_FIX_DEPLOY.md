# Quick Deployment Guide - Deduplication Fix

## What Changed

The deduplication logic now works **correctly** by executing **AFTER** storing new entries instead of **BEFORE**.

**Old behavior:** Create entry → Check for duplicates → Keeps both because first one is "newest"
**New behavior:** Create entry → Check for duplicates → Delete older ones, keep new one ✅

## Deployment Steps

### Step 1: Restart Flask (Activate Changes)
```bash
# If Flask is running, stop it
Ctrl+C

# Clear the screen
clear

# Restart Flask
python3 run.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * WARNING in app.run_wrapper...
```

### Step 2: Clear Test Data (Optional)
If you want to test from a clean slate:

```sql
-- In MySQL terminal
DELETE FROM log_entries WHERE app_id = 1;
```

### Step 3: Run the Test Script
```bash
# In a new terminal/tab
python3 test_dedup_fix.py
```

Expected output:
```
================================================================================
DEDUPLICATION TEST - Order of Operations Fix
================================================================================

Configuration:
  API Base URL: http://localhost:5000
  App ID: aj12
  Event Name: card_click1
  Test Strategy: Send same event 3 times, verify only latest is kept

--------------------------------------------------------------------------------
TEST 1: First trigger (baseline)
--------------------------------------------------------------------------------

[Trigger 1] Sending event...
  EventTime: 1762188400025
  ✅ Event sent successfully (ID: 500)

Result: 1 card_click1 event(s) in database
Expected: 1
Status: ✅ PASS

--------------------------------------------------------------------------------
TEST 2: Second trigger (deduplication should delete first)
--------------------------------------------------------------------------------

[Trigger 2] Sending event...
  EventTime: 1762188402100
  ✅ Event sent successfully (ID: 501)

Result: 1 card_click1 event(s) in database
Expected: 1 (first one should be deleted, only latest kept)
Status: ✅ PASS - Deduplication not working!

--------------------------------------------------------------------------------
TEST 3: Third trigger (should still be only 1, not 2 or 3)
--------------------------------------------------------------------------------

[Trigger 3] Sending event...
  EventTime: 1762188404250
  ✅ Event sent successfully (ID: 502)

Result: 1 card_click1 event(s) in database
Expected: 1 (only the latest event should be stored)
Status: ✅ PASS

================================================================================
FINAL VERIFICATION
================================================================================

Total events in database: 1

Latest card_click1 events:
  1. ID: 502, Created: 2025-11-03 16:47:15

✅ SUCCESS! Only 1 card_click1 event stored (latest one)
   Deduplication is working correctly!

================================================================================
```

### Step 4: Verify on Dashboard

1. Open http://localhost:5000/app/aj12 (or your app's detail page)
2. Check the event list
3. Verify: **No duplicate events showing**
4. Pagination should work correctly with accurate counts

### Step 5: Check Database (Optional)

Verify the fix at the database level:

```sql
-- Check card_click1 events
SELECT id, event_name, created_at FROM log_entries 
WHERE event_name = 'card_click1' 
ORDER BY created_at DESC
LIMIT 10;

-- Should show only 1 entry (the latest)

-- Check total count per event
SELECT event_name, COUNT(*) as count FROM log_entries 
WHERE app_id = 1 
GROUP BY event_name;

-- Each event_name should appear only once (the latest occurrence)
```

## Troubleshooting

### Issue: Still seeing multiple duplicates

**Solution:** 
1. Make sure Flask restarted (you should see the startup message)
2. Check Flask console for any error messages
3. Try clearing the database and restarting:
   ```sql
   DELETE FROM log_entries;
   ```

### Issue: Test script says "FAIL"

**Solution:**
1. Verify Flask is running (http://localhost:5000 should load)
2. Verify your app_id is correct (change "aj12" to your actual app_id in test script)
3. Check Flask console for validation errors

### Issue: Events still not deduplicating when triggered from app

**Solution:**
- Verify the payloads are EXACTLY identical (including nested `payload` object)
- Remember: Different `eventTime`, `identity`, `sessionId` values DON'T prevent deduplication
- Only different business data (items, card_name, payment_type, etc.) prevents deduplication

## Files Modified

- ✅ `app/services/log_service.py` - Deduplication now happens AFTER storing
- ✅ `app/repositories/log_repository.py` - `keep_id` parameter properly used
- 📄 `DEDUPLICATION_FIX.md` - Full technical explanation
- 📄 `test_dedup_fix.py` - Verification test script

## Expected Behavior After Fix

### Before sending any events:
```
DB: Empty
Dashboard: No events
```

### First `card_click1` event:
```
DB: 1 entry (ID 500)
Dashboard: 1 card_click1
```

### Second `card_click1` event (identical payload):
```
DB: 1 entry (ID 501) - ID 500 was deleted
Dashboard: 1 card_click1 (newest one)
```

### Third `card_click1` event (identical payload):
```
DB: 1 entry (ID 502) - ID 501 was deleted
Dashboard: 1 card_click1 (newest one)
```

**Result: Database size stays constant, only latest event kept** ✅

## Questions?

Refer to:
- `DEDUPLICATION_FIX.md` - Technical details and logic
- `test_dedup_fix.py` - Test to verify fix works
- `app/services/log_service.py` - Implementation
- `app/repositories/log_repository.py` - Dedup logic

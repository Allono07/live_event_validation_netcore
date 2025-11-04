# Event Deduplication (Option A) — Quick Start Guide

## What Was Implemented
When the same event arrives multiple times with the **same business content** (`eventName` + `payload`), **only the latest one is stored** in the database, regardless of **transient differences** like user identity, timestamp, or session ID. All older copies are automatically deleted.

### What Gets Ignored (Doesn't Affect Deduplication)
- `identity` — Who triggered the event
- `eventTime` — When it arrived
- `sessionId` — Which session
- `retry` count
- `networkMode`
- `attrParams`
- Any other metadata

### What Matters (Triggers Deduplication)
- `eventName` — The event type
- `payload` — The business data

---

## How to Test

### Option 1: Automated Test Script (RECOMMENDED)
```bash
python3 test_deduplication_option_a.py
```

This sends two `logout_event` with:
- ✅ **Same eventName** ("logout_event")
- ✅ **Same payload** (payment details, items)
- ❌ **Different identity** (one user vs. empty)
- ❌ **Different eventTime** (different timestamps)

**Expected result:**
```
✅ SUCCESS: Both logged out deduplicated despite different identity!
```

### Option 2: Manual API Test
```bash
# Send logout_event as User 8129445706
curl -X POST http://localhost:5000/api/logs/aj12 \
  -H "Content-Type: application/json" \
  -d '{
    "eventName":"logout_event",
    "identity":"8129445706",
    "eventTime":"1762184984976",
    "payload":{"payment_type":"alle","card_name":2}
  }'

# Send SAME logout_event as different user (empty identity)
curl -X POST http://localhost:5000/api/logs/aj12 \
  -H "Content-Type: application/json" \
  -d '{
    "eventName":"logout_event",
    "identity":"",
    "eventTime":"1762184992456",
    "payload":{"payment_type":"alle","card_name":2}
  }'

# View dashboard → should show only 1 "logout_event", not 2 ✅
```

### Option 3: Browser DevTools
1. Open app detail page for your app
2. Open DevTools → Network tab
3. Send events via your mobile app
4. Check dashboard event count
5. Verify only 1 "logout_event" shown despite multiple API calls

---

## Code Changes

**File:** `app/repositories/log_repository.py`

**Updated method:**
```python
@staticmethod
def _compute_payload_hash(payload: dict) -> str:
    """Hash only eventName + payload sub-object (ignore identity, eventTime, etc.)"""
    essential = {}
    if 'eventName' in payload:
        essential['eventName'] = payload['eventName']
    if 'payload' in payload:
        essential['payload'] = payload['payload']
    
    payload_json = json.dumps(essential, sort_keys=True, default=str)
    return hashlib.sha256(payload_json.encode()).hexdigest()
```

**Result:** Events with same business logic (eventName + payload) are now deduplicated, even if they differ in user context, timestamp, or other metadata.

---

## Real Example from Your Logs

```json
// logout_event #1 (timestamp: 1762184984976, user 8129445706)
{
  "eventName": "logout_event",
  "identity": "8129445706",
  "eventTime": "1762184984976",
  "payload": {"payment_type": "alle", "card_name": 2, "items": [...]}
}

// logout_event #2 (timestamp: 1762184992456, user empty)
{
  "eventName": "logout_event",
  "identity": "",
  "eventTime": "1762184992456",
  "payload": {"payment_type": "alle", "card_name": 2, "items": [...]}
}
```

**BEFORE Option A:** Both stored (2 entries) ❌  
**NOW with Option A:** Only latest stored (1 entry) ✅

---

## Deduplication Rules

**DEDUPLICATED** (counted as duplicates, only latest kept):
- Same `eventName` + `payload` → ✅ Only 1 stored

**NOT DEDUPLICATED** (both stored):
- Same `eventName`, **different `payload`** → Both kept
- **Different `eventName`**, same data → Both kept
- Events in different apps → Both kept

---

## Verification Steps

1. **Restart Flask:**
   ```bash
   python3 run.py
   ```

2. **Run test:**
   ```bash
   python3 test_deduplication_option_a.py
   ```

3. **Expected output:**
   ```
   ✅ SUCCESS: Both logged out deduplicated despite different identity!
   ✅ SUCCESS: Both new_event deduplicated despite different identity!
   ```

4. **Check dashboard:**
   - Navigate to app detail page
   - Verify no duplicate logout_event or new_event entries

5. **Database query:**
   ```sql
   SELECT event_name, COUNT(*) FROM log_entries 
   WHERE app_id = 1 GROUP BY event_name;
   ```
   Each event should appear only once (or expected number based on different payloads)

---

## What Changed

| Aspect | Before | After |
|--------|--------|-------|
| Same event, different user | 2 entries | 1 entry (latest) ✅ |
| Same event, different time | 2 entries | 1 entry (latest) ✅ |
| Same event, different payload | 2 entries | 2 entries (both kept) ✓ |

---

## Performance

- Hash computation: ~1ms per event
- Database query: Fast (indexed on app_id, event_name)
- Space saved: Instant deletion of older duplicates

---

## Next Steps

1. Restart the app
2. Run `python3 test_deduplication_option_a.py`
3. Verify ✅ SUCCESS messages
4. Check dashboard for no duplicate events
5. Monitor your app logs for deduplication in action

---

## Reference

- **Full docs:** `DEDUPLICATION.md`
- **Test script:** `test_deduplication_option_a.py`
- **Code change:** `app/repositories/log_repository.py` (`_compute_payload_hash()`)

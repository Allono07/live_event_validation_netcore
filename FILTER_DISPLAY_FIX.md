# Filter Display Fix - Show Event Header for Each Instance

## Problem
When filtering by an event that appears multiple times (e.g., 2 instances of `card_click1`):
- **Before:** Only one event header shown, all payload rows grouped under it
- **Expected:** Separate event header for each instance with its own timestamp

### Example:

**Before (Wrong):**
```
card_click1  |  16:46:46
payload1a    |  value1a
payload2a    |  value2a
payload3a    |  value3a
payload1b    |  value1b    ← Same event but different timestamp, no header!
payload2b    |  value2b
payload3b    |  value3b
```

**After (Correct):**
```
card_click1  |  16:46:46
payload1a    |  value1a
payload2a    |  value2a
payload3a    |  value3a

card_click1  |  16:47:15   ← Now has its own header!
payload1b    |  value1b
payload2b    |  value2b
payload3b    |  value3b
```

## Root Cause

The `applyFilters()` function grouped results by event name only:

```javascript
// OLD - Groups by event name only
const groups = {};
currentFilteredResults.forEach(r => {
    const ev = r.eventName || '';
    if (!groups[ev]) groups[ev] = [];
    groups[ev].push(r);  // All instances of 'card_click1' go here
});
```

This caused all instances of the same event to be collapsed into one group.

## Solution

Changed grouping to use both event name AND timestamp as the unique key:

```javascript
// NEW - Groups by event name + timestamp
const groups = {};
currentFilteredResults.forEach(r => {
    const ev = r.eventName || '';
    const ts = r.timestamp || '';
    const key = `${ev}|${ts}`;  // Unique per instance
    if (!groups[key]) groups[key] = [];
    groups[key].push(r);
});
```

Now each instance gets its own group with its own header showing the correct timestamp.

## Changes Made

**File:** `app/static/js/app_detail.js`

**Function:** `applyFilters()` - lines ~505-540

**Key changes:**
1. Create unique key per event instance: `eventName|timestamp`
2. Group results by this unique key
3. Sort by timestamp (newest first)
4. Render separate header for each instance with its timestamp

## How It Works

### Before Filtering:
```
allValidationResults = [
  { eventName: "card_click1", timestamp: "16:46:46", key: "payment_type", ... },
  { eventName: "card_click1", timestamp: "16:46:46", key: "card_name", ... },
  { eventName: "card_click1", timestamp: "16:47:15", key: "payment_type", ... },
  { eventName: "card_click1", timestamp: "16:47:15", key: "card_name", ... }
]
```

### After Grouping:
```
groups = {
  "card_click1|16:46:46": [payload1a, payload2a],
  "card_click1|16:47:15": [payload1b, payload2b]
}
```

### Rendered Table:
```
Header: card_click1  16:46:46
Row: payload1a
Row: payload2a
Header: card_click1  16:47:15  ← NEW: Separate header for 2nd instance
Row: payload1b
Row: payload2b
```

## Benefits

✅ **Clear separation** - Each event instance is visually distinct
✅ **Accurate timestamps** - See when each instance occurred
✅ **Better readability** - Easy to distinguish between multiple occurrences
✅ **Maintains filtering** - All other filter logic unchanged

## Testing

### Test Case 1: Single instance
1. Filter by `card_click1` (only 1 instance in logs)
2. **Expected:** 1 event header shown

### Test Case 2: Multiple instances, same payload
1. Send `card_click1` twice with identical payload
2. Filter by `card_click1`
3. **Expected:** 2 event headers (even though payload is same), each with different timestamp

### Test Case 3: Multiple instances, different payloads
1. Send `card_click1` with payload A, then payload B
2. Filter by `card_click1`
3. **Expected:** 2 event headers, each showing its own fields

### Test Case 4: Multiple events
1. Filter by multiple events (e.g., `card_click1` + `logout_event`)
2. **Expected:** Each event occurrence has its own header with correct timestamp

### Test Case 5: Sort order
1. Filter events with multiple instances spread over time
2. **Expected:** Headers sorted by timestamp (newest first)

## Example Scenario

**Database has:**
- `card_click1` at 16:46:46 with payload: {payment_type: "alle", card_name: 2}
- `card_click1` at 16:47:15 with payload: {payment_type: "alle", card_name: 2}

**User filters by `card_click1`:**

**Now shows:**
```
TIMESTAMP         EVENT NAME         FIELD NAME    VALUE    EXPECTED    RECEIVED    STATUS
16:47:15          card_click1        payment_type  alle     text        text        Valid
                                     card_name     2        integer     integer     Valid

16:46:46          card_click1        payment_type  alle     text        text        Valid
                                     card_name     2        integer     integer     Valid
```

Before the fix, the second instance (16:46:46) would have had no header!

## Deployment

Just restart Flask:
```bash
Ctrl+C
python3 run.py
```

Then test by filtering an event that appears multiple times in your database.

## Related Issues Fixed

- Grouped filtering now properly displays each event instance
- Download reports will also include proper grouping
- Filter search shows all event instances correctly

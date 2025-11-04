# Deduplication Fix - Order of Operations

## Problem Identified

You reported seeing **2 instances of the same `card_click1` event** in the database, and when triggered again, it stayed at 2 (not growing to 3, 4, 5, etc.). This indicated deduplication was partially working but not correctly.

### Root Cause

The deduplication was being called **BEFORE** storing the new entry:

```python
# OLD LOGIC (WRONG)
delete_duplicate_older_entries(app.id, event_name, payload)  # Delete old ones first
log_entry = create(...)                                       # Then store new one
```

This caused a problem:
1. **First trigger**: No duplicates exist → Can't delete anything → Store entry (ID 300)
2. **Second trigger**: Deduplication runs BEFORE storing
   - Finds ID 300 (has same payload)
   - Tries to delete it... but the logic keeps the first match (ID 300) as "newest"
   - So it doesn't delete ID 300
   - Then stores the new entry (ID 315)
   - Result: **2 entries in DB**
3. **Third trigger**: Same logic, but now ID 315 is kept, ID 300 was never deleted
   - Result: **Still only 2 entries** (dedup prevents growth beyond 2)

## Solution Implemented

Changed deduplication to happen **AFTER** storing the new entry:

```python
# NEW LOGIC (CORRECT)
log_entry = create(...)                                      # Store new one first
delete_duplicate_older_entries(app.id, event_name, payload, keep_id=log_entry.id)  # Then delete old ones
```

This ensures:
1. **First trigger**: Store entry (ID 300) → No old duplicates to delete
2. **Second trigger**: Store new entry (ID 315) → Delete ID 300 (older duplicate) → Keep only ID 315
3. **Third trigger**: Store new entry (ID 320) → Delete ID 315 (older duplicate) → Keep only ID 320
4. Result: **Always only 1 entry** per unique event

## Updated Method Signature

The `delete_duplicate_older_entries()` method now properly uses the `keep_id` parameter:

```python
def delete_duplicate_older_entries(self, app_id: int, event_name: str, payload: dict, keep_id: int = None) -> int:
    """Delete all older duplicate entries, keeping only the latest one.
    
    Args:
        app_id: Application ID (numeric)
        event_name: Event name (should be normalized/lowercase)
        payload: Event payload dict
        keep_id: ID of the entry to keep (usually the newly created one). If None, keeps the newest.
        
    Returns:
        Count of deleted entries
    """
    # If keep_id is provided, delete ALL other matches for this payload
    for log in all_entries:
        if _compute_payload_hash(log.payload) == payload_hash:
            if log.id != keep_id:
                db.session.delete(log)
                deleted_count += 1
```

## Files Modified

1. **`app/services/log_service.py`**
   - Removed deduplication check before storing entry (3 locations removed)
   - Added deduplication call after each entry creation (3 locations added)
   - Now passes `keep_id=log_entry.id` to preserve the newly created entry

2. **`app/repositories/log_repository.py`**
   - Updated `delete_duplicate_older_entries()` to use `keep_id` parameter
   - When `keep_id` is provided, explicitly deletes all entries except the one to keep
   - Better logic for respecting the new entry as the one to preserve

## Expected Behavior After Fix

### When the same event arrives multiple times:

```
Timeline:
├─ 16:46:46 → card_click1 (ID 300) stored
├─ 16:47:00 → card_click1 (ID 315) stored → ID 300 deleted → Only ID 315 remains
├─ 16:47:15 → card_click1 (ID 320) stored → ID 315 deleted → Only ID 320 remains
└─ Result: Always exactly 1 entry for each unique event payload
```

### Dashboard shows:
- Only **1 instance** of `card_click1` (the latest)
- No duplicate events accumulating
- Pagination works correctly with accurate total count

## Testing the Fix

1. **Clear existing logs**
   ```sql
   DELETE FROM log_entries;
   ```

2. **Restart Flask**
   ```bash
   python3 run.py
   ```

3. **Trigger the same event 3+ times** (e.g., `card_click1` with same payload)

4. **Verify in database**
   ```sql
   SELECT id, event_name, created_at FROM log_entries WHERE event_name = 'card_click1' ORDER BY created_at;
   ```
   - Should show **only 1 entry** (the latest one)

5. **Verify on dashboard**
   - Event list should show only 1 `card_click1`
   - No duplicates visible

## Option A Deduplication Still Active

Deduplication still uses **Option A** (eventName + payload sub-object only, ignoring metadata):
- Different `eventTime` values → Same event (deduplicated)
- Different `identity` values → Same event (deduplicated)
- Different `sessionId` values → Same event (deduplicated)
- Same business data → Only latest kept

This is working as designed.

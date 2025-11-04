# Stats Calculation Explained

## Overview
The dashboard displays four key metrics on the stats cards. Here's how each one is calculated:

## Stats Cards Breakdown

### 1. **Total User Events** (Blue Card)
- **Label**: "Total User Events"
- **Description**: "eventId != 0"
- **How it's calculated**: Counts unique event types captured in the last 24 hours

```python
total_events = set()
for log in logs:
    total_events.add(log.event_name)
return len(total_events)  # Unique event names
```

**Key Points**:
- Counts UNIQUE event types, not individual log entries
- Example: If you have 5 `UserLogin` events and 3 `PageView` events, Total = 2

### 2. **Passed** (Green Card)
- **How it's calculated**: Counts unique event types where **ALL fields passed validation**

```python
valid_events = set()
for log in logs:
    if log.validation_status == 'valid':
        # Check that ALL validation_results have 'Valid' status
        all_valid = all(
            result.get('validationStatus') == 'Valid' 
            for result in log.validation_results
        )
        if all_valid:
            valid_events.add(log.event_name)
return len(valid_events)  # Unique events where ALL fields are valid
```

**Example**:
- Event `card_click` with fields: payment_type (Valid), card_name (Valid), items (Valid) → **Counts as 1 Passed**
- Event `user_login` with fields: user_id (Valid), timestamp (Invalid) → **Does NOT count**

### 3. **Failed** (Red Card)
- **How it's calculated**: Counts unique event types where **at least ONE field failed validation**

```python
invalid_events = set()
for log in logs:
    if log.validation_status == 'invalid':
        invalid_events.add(log.event_name)
return len(invalid_events)  # Unique events with validation failures
```

### 4. **Success Rate** (Info Card - Light Blue)
- **How it's calculated**: `(Passed Events ÷ Total Events) × 100%`

```javascript
// In app_detail.js
const successRate = total > 0 ? Math.round((passed / total) * 100) : 0;
```

## Example Scenario

If your database contains these log entries over 24 hours:

**UserLogin events:**
- Entry 1: user_id (Valid), timestamp (Valid), device (Valid) → All valid ✅
- Entry 2: user_id (Valid), timestamp (Valid), device (Valid) → All valid ✅
- Entry 3: user_id (Valid), timestamp (Invalid), device (Valid) → Has failure ❌

**CardClick events:**
- Entry 4: payment_type (Valid), amount (Invalid) → Has failure ❌

**PageView events:**
- Entry 5: url (Valid), duration (Valid) → All valid ✅

**Result:**
- **Total**: 3 unique event types (UserLogin, CardClick, PageView)
- **Passed**: 2 events (UserLogin + PageView both have at least one fully-valid instance)
- **Failed**: 1 event (CardClick has failures)
- **Success Rate**: (2 ÷ 3) × 100 = 66.7% ≈ 67%

## Important Clarifications

### "Passed" Event Logic
- An event is considered **"Passed"** if there's at least ONE log entry for that event where **ALL fields are Valid**
- It only counts UNIQUE event types, not individual log entries
- If the same event appears 10 times but 5 have failures, it still counts as 1 "Passed" event (if at least one entry had all valid fields)

### Counting Method
- **Old (Incorrect)**: Counted total log entries
- **New (Correct)**: Counts unique event types based on their validation results

## Time Window
All stats are calculated for the **last 24 hours** by default:
- Can be customized via the `hours` query parameter on the `/app/<app_id>/stats` endpoint
- Example: `/app/<app_id>/stats?hours=12` for the last 12 hours

## How to Verify

### Via Database Query (More Complex Now)
```sql
-- Get all events with their validation info
SELECT DISTINCT event_name, validation_status, validation_results
FROM log_entries 
WHERE app_id = (SELECT id FROM app WHERE app_id = 'YOUR_APP_ID')
  AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY event_name;
```

Then manually check:
- Unique event names = Total
- Events with all "Valid" fields = Passed
- Events with any "Invalid" fields = Failed

### Via API Endpoint
```bash
curl http://localhost:5001/app/YOUR_APP_ID/stats
```

Response format:
```json
{
  "total": 3,
  "valid": 2,
  "invalid": 1,
  "error": 0
}
```

## Real-Time Updates
- Stats refresh every **5 seconds** on the dashboard (see JavaScript)
- Data is calculated on-demand when the endpoint is called
- Now includes deeper validation analysis

## Code Location
The stats calculation happens in:
- **File**: `app/repositories/log_repository.py`
- **Method**: `get_stats(app_id, hours=24)`
- **Called by**: `LogService.get_validation_stats()`
- **Endpoint**: `GET /app/<app_id>/stats`


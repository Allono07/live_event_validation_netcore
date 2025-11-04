# Event Coverage - Data Flow Diagram

## How Event Coverage is Calculated

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VALIDATION RULES (Sheet)                            │
│                                                                              │
│  event_name    │  field_name        │  data_type                           │
│  ───────────────────────────────────────────────────                        │
│  sign_up       │  user_id           │  integer                             │
│  sign_up       │  email             │  string                              │
│  sign_up       │  timestamp         │  date                                │
│  login         │  user_id           │  integer                             │
│  login         │  device            │  string                              │
│  purchase      │  product_id        │  integer                             │
│  purchase      │  amount            │  float                               │
│  appointment_click  │  app_id       │  integer                             │
│  product_click │  product_id        │  integer                             │
│                                                                              │
│  ➜ Distinct Events in Rules: {sign_up, login, purchase,                   │
│                               appointment_click, product_click}             │
│  ➜ Total = 5                                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DATABASE LOG ENTRIES                                  │
│                                                                              │
│  id │  app_id  │  event_name       │  payload          │  validation_...  │
│  ────────────────────────────────────────────────────────────────────────  │
│  1  │  123     │  sign_up          │  {...}            │  Valid           │
│  2  │  123     │  sign_up          │  {...}            │  Valid           │
│  3  │  123     │  login            │  {...}            │  Valid           │
│  4  │  123     │  login            │  {...}            │  Invalid         │
│  5  │  123     │  purchase         │  {...}            │  Valid           │
│                                                                              │
│  ➜ Distinct Events in Logs: {sign_up, login, purchase}                    │
│  ➜ Captured = 3                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COVERAGE CALCULATION                                     │
│                                                                              │
│  Rules Events: {sign_up, login, purchase, appointment_click,              │
│                 product_click}                                             │
│                                                                              │
│  Captured Events: {sign_up, login, purchase}                              │
│                                                                              │
│  Captured Count = 3                                                         │
│                                                                              │
│  Missing Events = Rules - Captured                                         │
│                 = {appointment_click, product_click}                       │
│  Missing Count = 2                                                          │
│                                                                              │
│  Total = 5                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  /app/<app_id>/coverage ENDPOINT                            │
│                                                                              │
│  Returns JSON:                                                              │
│  {                                                                           │
│    "captured": 3,                    // Count of distinct captured events  │
│    "missing": 2,                     // Count of rules not captured        │
│    "total": 5,                       // Total events in rules              │
│    "missing_events": [               // Event names not captured           │
│      "appointment_click",                                                   │
│      "product_click"                                                        │
│    ],                                                                        │
│    "event_names": [...]              // All events from rules              │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                FRONTEND - app_detail.js                                      │
│                                                                              │
│  updateCoverage() function:                                                 │
│  1. Fetch from /app/<app_id>/coverage                                       │
│  2. Display: Captured=3, Missing=2, Total=5                               │
│  3. List missing events: appointment_click, product_click                  │
│  4. Calculate fully valid events from allValidationResults                 │
│  5. Display as green badges                                                │
│  6. Call again in 10 seconds                                               │
│                                                                              │
│  Result displayed in Event Coverage card:                                  │
│  ┌─────────────────────────────────────────────────────┐                 │
│  │ Captured: 3 │ Missing: 2 │ Total in Sheet: 5      │                 │
│  ├─────────────────────────────────────────────────────┤                 │
│  │ Missing events:                                     │                 │
│  │  • appointment_click                                │                 │
│  │  • product_click                                    │                 │
│  ├─────────────────────────────────────────────────────┤                 │
│  │ Fully Valid Events:                                 │                 │
│  │  ✓ sign_up ✓ purchase                               │                 │
│  └─────────────────────────────────────────────────────┘                 │
│                                                                              │
│  Polling: setInterval(updateCoverage, 10000)                               │
│  Updates every 10 seconds as new logs arrive                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## SQL Queries Behind Coverage

### 1. Get Rules Event Names
```sql
SELECT DISTINCT event_name 
FROM validation_rules 
WHERE app_id = 123
ORDER BY event_name;

Result: {sign_up, login, purchase, appointment_click, product_click}
```

### 2. Get Captured Event Names
```sql
SELECT DISTINCT event_name 
FROM log_entries 
WHERE app_id = 123 
  AND event_name IS NOT NULL
ORDER BY event_name;

Result: {sign_up, login, purchase}
```

### 3. Calculate Coverage
```python
rules_events = {sign_up, login, purchase, appointment_click, product_click}
captured_events = {sign_up, login, purchase}

captured_count = len(captured_events)           # 3
total_count = len(rules_events)                 # 5
missing_events = rules_events - captured_events # {appointment_click, product_click}
missing_count = len(missing_events)             # 2
```

---

## Data Flow Timeline

```
T0: User uploads validation_rules.csv
    ├─ 5 events added to validation_rules table
    ├─ updateCoverage() called
    ├─ Captured: 0, Missing: 5, Total: 5
    └─ Shows all 5 events in "Missing events"

T1: First log event received (sign_up)
    ├─ Log entry stored in log_entries table
    ├─ coverage() endpoint updates on next poll
    ├─ Captured: 1, Missing: 4, Total: 5
    └─ Shows 4 remaining in "Missing events"

T2: Second log event received (login)
    ├─ Log entry stored
    ├─ Coverage updates
    ├─ Captured: 2, Missing: 3, Total: 5
    └─ Shows 3 remaining

T3: Third log event received (purchase)
    ├─ Log entry stored
    ├─ Coverage updates
    ├─ Captured: 3, Missing: 2, Total: 5
    ├─ Shows 2 remaining: appointment_click, product_click
    └─ Fully Valid Events: {sign_up, login, purchase} (if all valid)

T4: Days pass... appointment_click event never comes
    ├─ Captured remains: 3
    ├─ Missing remains: 2
    ├─ Total remains: 5
    └─ UI shows consistent status of what's still needed
```

---

## Key Implementation Details

### Backend (Python/Flask)

**File:** `app/controllers/dashboard_controller.py`

```python
@dashboard_bp.route('/app/<app_id>/coverage', methods=['GET'])
def get_coverage(app_id):
    # Get event names from validation rules (the "sheet")
    sheet_event_names = validation_service.get_event_names(app_id)
    
    # Get event names from captured logs
    captured_event_names = log_service.get_distinct_event_names(app_id)
    
    # Calculate coverage
    captured_count = len(set(captured_event_names))
    total_count = len(set(sheet_event_names))
    missing_events = set(sheet_event_names) - set(captured_event_names)
    missing_count = len(missing_events)
    
    return jsonify({
        'captured': captured_count,
        'missing': missing_count,
        'total': total_count,
        'missing_events': sorted(list(missing_events))
    })
```

### Frontend (JavaScript)

**File:** `app/static/js/app_detail.js`

```javascript
// Called on page load
updateCoverage();

// Called every 10 seconds
setInterval(updateCoverage, 10000);

function updateCoverage() {
    fetch(`/app/${APP_ID}/coverage`)
        .then(r => r.json())
        .then(data => {
            // Update UI with counts
            document.getElementById('coveredCount').textContent = data.captured;
            document.getElementById('missingCount').textContent = data.missing;
            document.getElementById('totalSheetCount').textContent = data.total;
            
            // Update missing events list
            document.getElementById('missingEventsList').innerHTML = 
                data.missing_events.map(e => `<li><small>${e}</small></li>`).join('');
            
            // Update fully valid events (from current logs)
            const fullyValid = calculateFullyValidEvents();
            document.getElementById('fullyValidEventsList').innerHTML = 
                fullyValid.map(e => `<span class="badge bg-success">${e}</span>`).join('');
        });
}
```

---

## Troubleshooting

### Coverage shows 0/0/0
**Cause:** No validation rules uploaded
**Fix:** Upload a CSV file with validation rules

### Coverage shows 0 captured but logs exist
**Cause:** Event names in logs don't match event names in rules (case-sensitive)
**Fix:** Ensure event names match exactly (case-sensitive)

### Missing events list is empty but coverage says 0 captured
**Cause:** The "0 captured" refers to distinct events, but some were captured
**Fix:** Check if you meant to have different event names

### Fully Valid Events empty even though logs show "Valid"
**Cause:** Some fields for event are Invalid, only shows if ALL are Valid
**Fix:** Fix invalid fields so all fields pass validation


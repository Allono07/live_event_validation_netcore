# Event Coverage Logic - Quick Reference

## Scenario Example

### Validation Rules (Sheet) Contains:
1. `sign_up` - event in rules
2. `login` - event in rules
3. `purchase` - event in rules
4. `appointment_click` - event in rules
5. `product_click` - event in rules

**Total in Sheet = 5 events**

---

### Logs Database Contains (Captured):
- Event: `sign_up` (has records)
- Event: `login` (has records)
- Event: `purchase` (has records)

**Total Captured = 3 events**

---

### Event Coverage Display

```
Event Coverage
Shows how many events from the rule sheet have been captured

┌─────────────────────────────────────────────────────────────┐
│  Captured  │  Missing  │  Total in Sheet                     │
│     3      │     2     │        5                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Missing events                  │ Fully Valid Events          │
│ • appointment_click             │ ✓ sign_up  ✓ purchase      │
│ • product_click                 │ ✓ login                    │
└─────────────────────────────────────────────────────────────┘
```

### What Each Column Means

| Column | Value | Meaning |
|--------|-------|---------|
| **Captured** | 3 | Number of distinct event types that have been captured/logged |
| **Missing** | 2 | Number of events defined in validation rules but NOT YET captured |
| **Total in Sheet** | 5 | Total number of events defined in the validation rules |
| **Missing events** | appointment_click, product_click | List of events from the rule sheet that haven't been captured yet |
| **Fully Valid Events** | sign_up, purchase, login | Events where ALL payload fields passed validation |

---

## Data Sources

### Captured Count
**Source:** Distinct event names in `log_entries` table
```sql
SELECT DISTINCT event_name FROM log_entries WHERE app_id = ? AND event_name IS NOT NULL
```

### Total Count
**Source:** Distinct event names in `validation_rules` table
```sql
SELECT DISTINCT event_name FROM validation_rules WHERE app_id = ?
```

### Missing Events
**Calculation:** Events in validation rules NOT in captured logs
```
Missing = Rules Events - Captured Events
Example: {sign_up, login, purchase, appointment_click, product_click} - {sign_up, login, purchase}
        = {appointment_click, product_click}
```

### Fully Valid Events
**Calculation:** Events where ALL validation results have status "Valid"
```
For each event name:
  - Collect all validation results for that event
  - If ALL results have validationStatus == "Valid"
    → Add to Fully Valid list
```

---

## Backend Endpoint

### GET `/app/<app_id>/coverage`

**Request:**
```
GET /api/app/my-app-123/coverage
```

**Response:**
```json
{
    "captured": 3,
    "missing": 2,
    "total": 5,
    "missing_events": ["appointment_click", "product_click"],
    "event_names": ["sign_up", "login", "purchase", "appointment_click", "product_click"]
}
```

---

## Frontend Implementation

### JavaScript updateCoverage()

```javascript
function updateCoverage() {
    fetch(`/app/${APP_ID}/coverage`)
        .then(response => response.json())
        .then(data => {
            // Display counts
            document.getElementById('coveredCount').textContent = data.captured;     // 3
            document.getElementById('missingCount').textContent = data.missing;      // 2
            document.getElementById('totalSheetCount').textContent = data.total;     // 5
            
            // Display missing event names
            const missingList = document.getElementById('missingEventsList');
            missingList.innerHTML = data.missing_events
                .map(e => `<li><small>${e}</small></li>`)
                .join('');
            
            // Display fully valid events (calculated from logs)
            const fullyValid = calculateFullyValidEvents();  // ['sign_up', 'purchase', 'login']
            const validList = document.getElementById('fullyValidEventsList');
            validList.innerHTML = fullyValid
                .map(e => `<span class="badge bg-success">${e}</span>`)
                .join('');
        });
}
```

### Called Periodically
```javascript
// Update coverage every 10 seconds
setInterval(updateCoverage, 10000);
```

---

## Common Scenarios

### Scenario 1: No Rules Uploaded
- **Captured:** 0
- **Missing:** 0
- **Total:** 0
- **Missing events:** (empty)
- **Fully Valid Events:** (empty)

### Scenario 2: Rules Uploaded, No Logs Yet
- **Captured:** 0
- **Missing:** 5 (all events from rules)
- **Total:** 5
- **Missing events:** sign_up, login, purchase, appointment_click, product_click
- **Fully Valid Events:** (empty - no logs yet)

### Scenario 3: All Rules Captured, Some Invalid
- **Captured:** 5 (all events captured)
- **Missing:** 0 (all events captured)
- **Total:** 5
- **Missing events:** (empty)
- **Fully Valid Events:** sign_up, purchase (if these 100% valid)

### Scenario 4: All Rules Captured, All Valid
- **Captured:** 5
- **Missing:** 0
- **Total:** 5
- **Missing events:** (empty)
- **Fully Valid Events:** sign_up, login, purchase, appointment_click, product_click

---

## Debug Tips

If coverage not updating:
1. Check browser console for errors
2. Verify validation rules are uploaded
3. Verify logs are being captured
4. Check network tab - is `/app/<app_id>/coverage` endpoint responding?
5. Check response has correct JSON structure

If counts are wrong:
- **Captured too low?** → Logs might not be stored in database, check `/app/<app_id>/logs` endpoint
- **Missing too low?** → Validation rules might not be loaded, check database
- **Total wrong?** → Check `validation_rules` table has correct entries


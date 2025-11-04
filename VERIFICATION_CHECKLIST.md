# Option A Implementation — Verification Checklist

## Pre-Deployment Checks

### Code Changes
- [x] Updated `_compute_payload_hash()` in `app/repositories/log_repository.py`
- [x] Method now hashes only `eventName` + `payload` sub-object
- [x] Transient fields (`identity`, `eventTime`, etc.) are ignored
- [x] Other methods (`find_duplicate()`, `delete_duplicate_older_entries()`) unchanged
- [x] `process_log()` in `app/services/log_service.py` unchanged (already calls dedup)

### Documentation
- [x] Created `DEDUPLICATION_OPTION_A.md` (quick start)
- [x] Updated `DEDUPLICATION.md` (full technical docs)
- [x] Created `OPTION_A_SUMMARY.md` (executive summary)
- [x] Visual docs `DEDUPLICATION_FLOW.md` explains Option A

### Test Coverage
- [x] Created `test_deduplication_option_a.py` with your actual data
- [x] Tests with `logout_event` (different identity, same payload)
- [x] Tests with `new_event` (different identity, same payload)
- [x] Both should deduplicate and show ✅ SUCCESS

---

## Deployment Steps

1. **Stop Flask** (if running)
   ```bash
   # Ctrl+C in terminal
   ```

2. **Restart Flask** (activates code changes)
   ```bash
   python3 run.py
   ```

3. **Wait for startup**
   - Should show: `Running on http://127.0.0.1:5000`
   - No errors in console

4. **Run test script**
   ```bash
   python3 test_deduplication_option_a.py
   ```

5. **Expected output**
   ```
   ============================================================
   OPTION A DEDUPLICATION TEST: eventName + payload only
   ============================================================
   
   [TEST CASE 1] logout_event with DIFFERENT identity values
   ...
   [RESULT] Total 'logout_event' entries: 1
   ✅ SUCCESS: Both logged out deduplicated despite different identity!
   
   [TEST CASE 2] new_event with DIFFERENT identity values
   ...
   [RESULT] Total 'new_event' entries: 1
   ✅ SUCCESS: Both new_event deduplicated despite different identity!
   ```

---

## Post-Deployment Verification

### Database Check
```bash
# Open MySQL/SQLite CLI
mysql -u <user> -p <database>
# or
sqlite3 validation_dashboard.db

# Query
SELECT event_name, COUNT(*) as count FROM log_entries 
WHERE app_id = (SELECT id FROM apps WHERE app_id = 'aj12')
GROUP BY event_name;
```

Expected: No event appears more than once if it has the same payload.

### Dashboard Check
1. Open app detail page (http://localhost:5000/app/aj12)
2. Check "Live Validation Results" section
3. Look for `logout_event` and `new_event` entries
4. Should see only 1 of each (latest timestamp)
5. Older duplicates should not appear

### Browser DevTools Check
1. Open app detail page
2. Open DevTools → Network tab
3. Refresh page
4. Find `/app/aj12/logs?limit=50&page=1` request
5. Check response JSON
6. Verify `logout_event` count is 1 (not multiple)

### API Direct Test
```bash
# Send logout_event with user 8129445706
curl -X POST http://localhost:5000/api/logs/aj12 \
  -H "Content-Type: application/json" \
  -d '{"eventName":"logout_event","identity":"user1","payload":{"payment_type":"alle"}}'

# Send same logout_event with user empty
curl -X POST http://localhost:5000/api/logs/aj12 \
  -H "Content-Type: application/json" \
  -d '{"eventName":"logout_event","identity":"","payload":{"payment_type":"alle"}}'

# Verify only 1 logout_event stored
curl http://localhost:5000/app/aj12/logs?limit=100&page=1 | grep -i logout
```

---

## Rollback Plan (If Needed)

If something goes wrong:

1. **Revert code**
   ```bash
   git checkout app/repositories/log_repository.py
   ```

2. **Restart Flask**
   ```bash
   python3 run.py
   ```

3. This returns to full-payload-hash behavior (original implementation).

---

## Performance Baseline

Test on your actual app to establish baseline:

**Run test script and note:**
- Execution time
- Number of deduped events
- Database size before/after

Example:
```
- Test execution: 5 seconds
- Events sent: 4 (2 logout_event, 2 new_event)
- Events deduplicated: 2
- Events stored: 2
- Space saved: ~200 bytes
```

---

## Monitoring After Deployment

### Flask Console
Watch for deduplication activity:
- No errors during event processing
- Events processed normally
- WebSocket updates work

### Database Size
```sql
-- Check size
SELECT 
  (SELECT COUNT(*) FROM log_entries) as total_logs,
  (SELECT COUNT(DISTINCT event_name) FROM log_entries) as unique_events,
  (SELECT COUNT(*) FROM log_entries WHERE app_id = 1) as app_logs;
```

Should show reasonable numbers (no explosion of entries).

### Event Stats
```sql
-- See distribution
SELECT event_name, COUNT(*) FROM log_entries 
GROUP BY event_name 
ORDER BY COUNT(*) DESC;
```

Should see realistic counts (not duplicates).

---

## Success Criteria

✅ **Deployment successful when:**

1. Flask starts without errors
2. Test script shows ✅ SUCCESS for both test cases
3. Dashboard shows correct event counts (no false duplicates)
4. Database has no duplicate entries for same event
5. API `/logs` endpoint returns correct counts
6. WebSocket real-time updates still work
7. No errors in Flask console

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Test script shows "FAILURE" | Restart Flask; ensure DB has data |
| Dashboard still shows duplicates | Clear browser cache; hard refresh |
| Events not appearing on dashboard | Check that events are in DB: `SELECT COUNT(*) FROM log_entries;` |
| Flask won't start | Check for syntax errors: `python3 -m py_compile app/repositories/log_repository.py` |
| Database locked errors | Ensure only one Flask instance is running |

---

## Rollforward (Next Steps)

After successful deployment:

1. **Monitor** for 1 hour to ensure stability
2. **Check logs** for any errors or warnings
3. **Ask users** if they notice improvement (no duplicate events)
4. **Document** in release notes: "Implemented Option A deduplication"

---

## Approval Checklist

Before going live, confirm:

- [ ] Code reviewed and no syntax errors
- [ ] Test script runs successfully
- [ ] Dashboard verified for correctness
- [ ] Database query confirms deduplication working
- [ ] No performance degradation observed
- [ ] Rollback plan ready if needed
- [ ] Team notified of change

---

## Sign-Off

Once all checks pass:

✅ **Option A Deduplication is LIVE**

Events with same `eventName` + `payload` are now deduplicated automatically, regardless of user context or timestamp differences.

Dashboard will show cleaner, more accurate event data without false duplicates.

---

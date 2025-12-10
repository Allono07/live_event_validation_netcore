# Quick Start: Async Event Processing

## What Changed?

Your API now uses **async event processing**:
- Events are **validated instantly** (< 10ms)
- **Queued to Redis** (< 1ms)
- API returns immediately with **202 Accepted**
- **Background workers** store in database

This allows handling **500+ req/min** instead of 50 req/min.

## Step 1: Verify Services Running

```bash
# Check PostgreSQL
psql -U allen -d live_validation_dashboard -c "SELECT 1;"
# Should return: 1

# Check Redis
redis-cli ping
# Should return: PONG
```

## Step 2: Install/Update Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Key new packages:
- `celery==5.3.4` - Task queue
- `redis==5.0.1` - Message broker

## Step 3: Start Flask App

```bash
# Terminal 1
source venv/bin/activate
python run.py

# You should see:
# 🗄️  Using database: postgresql://allen:netcore@localhost:5432/live_validation_dashboard
# ✅ Celery initialized
# Running on http://127.0.0.1:5001
```

## Step 4: Start Celery Worker

```bash
# Terminal 2 (new terminal in same directory)
bash start_celery_worker.sh

# You should see:
# 🔄 Starting Celery worker...
# ✅ Redis is running
# ---------- celery@your-machine v5.3.4 (oat)
#  ---- **** -----
#  --- * ***  * -- Darwin-...
#  -- * - **** -----
#  - ** ---------- [config]
#  - ** ---------- [queues]
#      . default
#      . emails
#      . batch_processing
#  [2025-12-10 15:45:00,123: INFO/MainProcess] Connected to redis://localhost:6379/0
```

## Step 5: Test the Async Flow

```bash
# Create a test app first (via web UI or manually)
curl -X POST http://localhost:5001/api/logs/test-app \
  -H "Content-Type: application/json" \
  -d '{
    "eventName": "user_login",
    "userId": 123,
    "timestamp": "2025-12-10T15:45:00Z"
  }'

# Response should be 202 Accepted:
# {
#   "event_name": "user_login",
#   "status": "valid",
#   "task_id": "abc-def-123",
#   "message": "Event queued for processing"
# }
```

Check Flask logs (Terminal 1):
```
2025-12-10 15:45:00 - app - INFO - Processing event: user_login
2025-12-10 15:45:00 - app - INFO - ✅ Validation PASSED for app_id: test-app
```

Check Celery logs (Terminal 2):
```
[2025-12-10 15:45:00,456: INFO/ForkPoolWorker-1] Task app.tasks.process_event_async[abc-def-123] succeeded in 0.125s: {
  'status': 'success',
  'log_entry_id': 1,
  'message': 'Event stored with ID 1'
}
```

## Step 6: Verify Data Stored

```bash
# Check if event was stored in database
psql -U allen -d live_validation_dashboard -c \
  "SELECT id, event_name, validation_status, created_at FROM log_entries ORDER BY created_at DESC LIMIT 5;"

# Should show your event with status 'valid'
```

## What's Different?

### API Response
```diff
- HTTP 200 OK (after database write)
+ HTTP 202 Accepted (immediately)
```

### Timeline
```
Before:
Validate → Database Write → Return (50-100ms)

After:
Validate → Queue to Redis → Return (5-10ms)
                          ↓
                     Background Worker writes database
```

### Handling Spikes
```
Before: Too many requests? Database locks up ❌

After: Requests pile up in Redis queue → Workers process at their pace ✅
```

## Monitoring

### View Queue Status
```bash
redis-cli
> LLEN celery          # Number of queued tasks
> HGETALL celery-task # Task details
```

### View Worker Status
```bash
celery -A app.tasks inspect active_queues
celery -A app.tasks inspect registered_tasks
celery -A app.tasks inspect stats
```

### Real-time Monitoring (Optional)
```bash
# Install Flower web UI
pip install flower

# Start Flower
celery -A app.tasks flower

# Open http://localhost:5555 in browser
```

## Troubleshooting

### Tasks Not Processing
```bash
# Check if worker is running
ps aux | grep celery

# Check if Redis has tasks
redis-cli LLEN celery

# Check Celery logs for errors
celery -A app.tasks worker -l debug
```

### Database Not Receiving Events
```bash
# Check if PostgreSQL is accepting connections
psql -U allen -d live_validation_dashboard -c "SELECT NOW();"

# Check log_entries table
psql -U allen -d live_validation_dashboard -c "SELECT COUNT(*) FROM log_entries;"
```

### High Queue Backlog
```bash
# Scale up: Run more workers
bash start_celery_worker.sh &  # Run in background
bash start_celery_worker.sh    # Run another one
```

## Performance Expectations

| Metric | Target | Typical |
|--------|--------|---------|
| API response time | <20ms | 5-10ms |
| Validation time | <10ms | 2-5ms |
| Queue-to-DB time | <1s | 100-300ms |
| Peak throughput | 500 req/min | 600+ req/min |
| Queue buffer capacity | ∞ (Redis) | ~100K events |

## Next: Load Testing

```bash
# Test with 500 req/min load
python test_load.py --rate 500 --duration 60

# Monitor in separate terminal
watch -n 1 'redis-cli LLEN celery'
```

## Documentation

- Full guide: `ASYNC_EVENT_PROCESSING.md`
- Scalability plan: `SCALABILITY_PLAN.md`
- Configuration: `celery_config.py`

## Still Have Issues?

Check logs in this order:
1. Flask logs (Terminal 1)
2. Celery logs (Terminal 2)
3. PostgreSQL logs: `psql -U allen -d live_validation_dashboard -c "SELECT pg_current_wal_lsn();"`
4. Redis: `redis-cli INFO`

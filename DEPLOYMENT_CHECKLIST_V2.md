# Scalability Deployment Checklist

## Phase 1: Database Migration (Week 1)

### PostgreSQL Installation & Setup
- [ ] Install PostgreSQL (version 14+)
  ```bash
  # macOS
  brew install postgresql@15
  brew services start postgresql@15
  
  # Ubuntu/Debian
  sudo apt-get install postgresql postgresql-contrib
  sudo service postgresql start
  ```

- [ ] Verify PostgreSQL installation
  ```bash
  psql --version
  psql -U postgres -c "SELECT version();"
  ```

- [ ] Create database and user
  ```bash
  createdb live_validation_dashboard
  createuser dashboard_user
  ```

- [ ] Set environment variables in `.env`
  ```bash
  DATABASE_URL=postgresql://dashboard_user:password@localhost:5432/live_validation_dashboard
  ```

- [ ] Run migration script
  ```bash
  python migrate_to_postgres.py
  ```

- [ ] Verify data migration
  ```bash
  # Check record counts match between SQLite and PostgreSQL
  python -c "
  import sqlite3
  import psycopg2
  # Compare counts
  "
  ```

- [ ] Create database indexes
  ```sql
  -- Run SQL from SCALABILITY_IMPLEMENTATION.md
  ```

- [ ] Update Flask configuration in `config/config.py`
  ```python
  SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
  SQLALCHEMY_ENGINE_OPTIONS = {
      'pool_size': 20,
      'pool_recycle': 3600,
      'pool_pre_ping': True,
  }
  ```

- [ ] Test database connection
  ```bash
  python run.py
  # Check for connection errors
  ```

---

## Phase 2: Redis Caching Layer (Week 1-2)

### Redis Installation & Setup
- [ ] Install Redis
  ```bash
  # macOS
  brew install redis
  brew services start redis
  
  # Ubuntu/Debian
  sudo apt-get install redis-server
  sudo service redis-server start
  ```

- [ ] Verify Redis installation
  ```bash
  redis-cli ping  # Should return PONG
  ```

- [ ] Set Redis URL in `.env`
  ```bash
  REDIS_URL=redis://localhost:6379/0
  ```

- [ ] Create cache service wrapper
  ```python
  # app/services/cache_service.py
  # Methods: get(), set(), delete(), clear()
  ```

- [ ] Configure Flask-Session with Redis
  ```python
  # In config/config.py
  SESSION_TYPE = 'redis'
  SESSION_REDIS = redis.from_url(REDIS_URL)
  ```

- [ ] Add caching to endpoints
  ```python
  # Cache frequently accessed data
  # - Validation rules (5 min TTL)
  # - App configuration (10 min TTL)
  # - User profiles (15 min TTL)
  ```

- [ ] Monitor cache hit ratio
  ```bash
  redis-cli INFO stats
  ```

---

## Phase 3: Application Server (Week 2)

### Gunicorn Configuration
- [ ] Verify Gunicorn is installed
  ```bash
  pip install gunicorn==21.2.0
  gunicorn --version
  ```

- [ ] Create `gunicorn_config.py`
  ```bash
  # File already created, verify settings:
  # workers = cpu_count * 2 + 1
  # worker_class = 'sync'
  # timeout = 60
  # max_requests = 1000
  ```

- [ ] Test Gunicorn locally
  ```bash
  gunicorn --config gunicorn_config.py 'app:create_app()'
  # Should show: "✅ Gunicorn is ready"
  ```

- [ ] Verify workers are spawned
  ```bash
  ps aux | grep gunicorn
  # Should show multiple worker processes
  ```

- [ ] Test load balancing
  ```bash
  curl http://127.0.0.1:8000/health
  # Should return JSON response
  ```

---

## Phase 4: Reverse Proxy (Week 2-3)

### Nginx Configuration
- [ ] Install Nginx
  ```bash
  # macOS
  brew install nginx
  
  # Ubuntu/Debian
  sudo apt-get install nginx
  ```

- [ ] Verify Nginx installation
  ```bash
  nginx -v
  ```

- [ ] Copy Nginx configuration
  ```bash
  # Linux
  sudo cp nginx.conf /etc/nginx/sites-available/live-validation-dashboard
  sudo ln -s /etc/nginx/sites-available/live-validation-dashboard /etc/nginx/sites-enabled/
  
  # macOS
  cp nginx.conf $(brew --prefix nginx)/etc/nginx/nginx.conf
  ```

- [ ] Test Nginx configuration
  ```bash
  # Linux
  sudo nginx -t
  
  # macOS
  nginx -t
  ```

- [ ] Reload Nginx
  ```bash
  # Linux
  sudo systemctl reload nginx
  
  # macOS
  brew services restart nginx
  ```

- [ ] Test reverse proxy
  ```bash
  curl http://localhost/
  # Should route to Gunicorn workers
  ```

- [ ] Enable gzip compression
  ```bash
  # Verify in nginx.conf
  gzip on;
  gzip_types text/plain text/css application/json application/javascript;
  ```

- [ ] Configure rate limiting
  ```bash
  # Verify in nginx.conf
  limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
  ```

---

## Phase 5: Performance Optimization (Week 3)

### Database Optimization
- [ ] Verify indexes are created
  ```sql
  SELECT * FROM pg_indexes WHERE tablename IN ('users', 'apps', 'log_entries', 'validation_rules', 'otps');
  ```

- [ ] Analyze query performance
  ```sql
  EXPLAIN ANALYZE SELECT * FROM log_entries WHERE app_id = 1;
  ```

- [ ] Optimize N+1 queries
  - [ ] Use SQLAlchemy eager loading where needed
  - [ ] Use `joinedload` or `selectinload` for relationships

- [ ] Add query pagination
  - [ ] Implement limit/offset in log retrieval
  - [ ] Default page size: 50 records

- [ ] Monitor slow queries
  ```sql
  ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
  SELECT pg_reload_conf();
  ```

### API Optimization
- [ ] Add response caching headers
  ```python
  @app.route('/api/apps')
  def get_apps():
      response = jsonify(apps)
      response.cache_control.max_age = 300  # 5 minutes
      return response
  ```

- [ ] Implement API compression
  ```bash
  # Verify in Nginx config
  gzip on;
  ```

- [ ] Add health check endpoint
  ```python
  @app.route('/health')
  def health():
      return {'status': 'healthy', 'timestamp': datetime.utcnow()}
  ```

---

## Phase 6: Monitoring & Logging (Week 4)

### Application Monitoring
- [ ] Install monitoring tools
  ```bash
  pip install prometheus-client==0.19.0
  pip install python-json-logger==2.0.7
  ```

- [ ] Add Prometheus metrics
  ```python
  # app/metrics.py
  # Track: request count, response time, errors, DB connection pool
  ```

- [ ] Configure structured logging
  ```python
  # app/utils/logging_utils.py
  # Use JSON format for ELK integration
  ```

- [ ] Setup health check endpoint
  ```bash
  # Already configured in app
  curl http://localhost/health
  ```

### Log Monitoring
- [ ] Configure Nginx access logs
  ```bash
  access_log /var/log/nginx/live_dashboard_access.log main;
  ```

- [ ] Configure Gunicorn error logs
  ```bash
  errorlog /var/log/gunicorn/live_dashboard_error.log
  ```

- [ ] Setup log rotation
  ```bash
  # Create /etc/logrotate.d/live-dashboard
  /var/log/nginx/live_dashboard*.log {
      daily
      rotate 14
      compress
      delaycompress
      notifempty
      create 0640 www-data www-data
      sharedscripts
  }
  ```

---

## Phase 7: Load Testing (Week 4)

### Load Testing Execution
- [ ] Install load testing tools
  ```bash
  pip install locust==2.19.1  # Optional: alternative to our test script
  ```

- [ ] Run baseline test (no load)
  ```bash
  python test_load.py
  # Expected: P50 < 100ms, P95 < 300ms, P99 < 500ms
  ```

- [ ] Run light load test (50 requests)
  ```bash
  python test_load.py --requests 50 --workers 5
  ```

- [ ] Run medium load test (100 requests)
  ```bash
  python test_load.py --requests 100 --workers 10
  ```

- [ ] Run heavy load test (200 requests)
  ```bash
  python test_load.py --requests 200 --workers 20
  ```

- [ ] Verify targets met
  - [ ] Success rate > 99%
  - [ ] P50 response time < 100ms
  - [ ] P95 response time < 300ms
  - [ ] P99 response time < 500ms

- [ ] Monitor system during test
  ```bash
  # Terminal 1: Monitor PostgreSQL
  watch -n 1 'psql -c "SELECT sum(numbackends) FROM pg_stat_database;"'
  
  # Terminal 2: Monitor Redis
  redis-cli --stat
  
  # Terminal 3: Monitor CPU/Memory
  top -o %CPU
  ```

### Bottleneck Analysis
- [ ] Check database connection pool
  ```python
  pool = db.engine.pool
  print(f"Checked out: {pool.checkedout()}")
  print(f"Overflow: {pool.overflow()}")
  ```

- [ ] Check Redis performance
  ```bash
  redis-cli --latency
  ```

- [ ] Check Gunicorn worker utilization
  ```bash
  ps aux | grep gunicorn | wc -l
  ```

- [ ] Check Nginx status
  ```bash
  curl http://127.0.0.1:8888/nginx_status  # If monitoring server enabled
  ```

---

## Phase 8: Production Deployment (Week 5)

### Pre-Deployment Checklist
- [ ] All tests passing
  ```bash
  pytest tests/
  ```

- [ ] Code review completed
  - [ ] All authentication flows working
  - [ ] All security headers configured
  - [ ] All secrets in environment variables

- [ ] Backup production database
  ```bash
  pg_dump live_validation_dashboard > backup.sql
  ```

- [ ] Test disaster recovery
  ```bash
  # Restore from backup to test database
  psql test_db < backup.sql
  ```

- [ ] SSL certificate ready (if HTTPS)
  ```bash
  # Using Let's Encrypt
  sudo certbot certonly --webroot -w /var/www/html -d yourdomain.com
  ```

### Deployment Steps
- [ ] Create systemd service (Linux)
  ```bash
  sudo tee /etc/systemd/system/live-dashboard.service > /dev/null << 'EOF'
  [Unit]
  Description=Live Validation Dashboard
  After=network.target postgresql.service redis.service
  
  [Service]
  ExecStart=/path/to/venv/bin/gunicorn --config gunicorn_config.py 'app:create_app()'
  Restart=always
  
  [Install]
  WantedBy=multi-user.target
  EOF
  
  sudo systemctl enable live-dashboard
  sudo systemctl start live-dashboard
  ```

- [ ] Verify all services running
  ```bash
  # PostgreSQL
  sudo systemctl status postgresql
  
  # Redis
  sudo systemctl status redis-server
  
  # Nginx
  sudo systemctl status nginx
  
  # Application
  sudo systemctl status live-dashboard
  ```

- [ ] Test full application flow
  - [ ] User registration working
  - [ ] OTP verification working
  - [ ] Login successful
  - [ ] Dashboard loading
  - [ ] API endpoints responsive

- [ ] Verify performance targets
  ```bash
  python test_load.py
  # Should show: Success rate > 99%, P95 < 300ms
  ```

- [ ] Setup monitoring alerts
  - [ ] CPU usage > 80%
  - [ ] Memory usage > 80%
  - [ ] Database connections > 90%
  - [ ] Error rate > 1%

---

## Performance Targets Summary

### Response Time Targets
| Metric | Target | Status |
|--------|--------|--------|
| P50 | < 100ms | ⏳ |
| P95 | < 300ms | ⏳ |
| P99 | < 500ms | ⏳ |
| Average | < 150ms | ⏳ |

### Throughput Targets
| Metric | Target | Status |
|--------|--------|--------|
| Requests/min | 500 | ⏳ |
| Concurrent users | 50-100 | ⏳ |
| Database connections | 20-30 | ⏳ |
| Cache hit ratio | 70-80% | ⏳ |

### Reliability Targets
| Metric | Target | Status |
|--------|--------|--------|
| Success rate | > 99% | ⏳ |
| Availability | > 99.9% | ⏳ |
| Data loss | Zero | ⏳ |

---

## Rollback Plan

If something goes wrong:

1. **Stop application**
   ```bash
   sudo systemctl stop live-dashboard
   ```

2. **Restore previous database**
   ```bash
   psql live_validation_dashboard < backup.sql
   ```

3. **Revert code changes**
   ```bash
   git revert <commit-hash>
   ```

4. **Restart with SQLite (temporary)**
   ```bash
   # Update config to use SQLite
   # SQLALCHEMY_DATABASE_URI = 'sqlite:///validation_dashboard.db'
   python run.py
   ```

5. **Post-mortem**
   - Identify root cause
   - Update deployment process
   - Re-test before retry

---

## Helpful Commands

### Database Management
```bash
# Connect to database
psql -U dashboard_user -d live_validation_dashboard

# Backup database
pg_dump -U dashboard_user live_validation_dashboard > backup.sql

# Restore database
psql -U dashboard_user live_validation_dashboard < backup.sql

# Check database size
psql -U dashboard_user -c "SELECT pg_size_pretty(pg_database_size('live_validation_dashboard'));"
```

### Redis Management
```bash
# Connect to Redis
redis-cli

# Check memory usage
redis-cli INFO memory

# Monitor commands
redis-cli MONITOR

# Flush cache
redis-cli FLUSHDB

# Check key count
redis-cli DBSIZE
```

### Gunicorn Management
```bash
# Start with custom bind
gunicorn --bind 127.0.0.1:8000 --workers 4 'app:create_app()'

# Check worker processes
ps aux | grep gunicorn

# Graceful reload (no downtime)
kill -HUP <gunicorn-master-pid>

# Check Gunicorn status
systemctl status live-dashboard
```

### Nginx Management
```bash
# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# View access logs
tail -f /var/log/nginx/live_dashboard_access.log

# View error logs
tail -f /var/log/nginx/live_dashboard_error.log

# Monitor connections
watch -n 1 'netstat -an | grep ESTABLISHED | wc -l'
```

---

## Success Criteria

✅ All items checked = Ready for production!

Once all phases complete:
1. Application handles 500 requests/min consistently
2. Response times meet SLA targets (P95 < 300ms)
3. Database performs well under load
4. Monitoring and alerts configured
5. Team trained on deployment process
6. Disaster recovery plan tested
7. Documentation complete


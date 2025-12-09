# Scalability Plan - 500 Requests/Min

## Current Architecture Analysis

### Bottlenecks Identified
1. **Single SQLite Database** - Not suitable for concurrent requests
2. **Synchronous Request Processing** - Flask default is blocking
3. **No Caching Layer** - Database queries on every request
4. **No Message Queue** - Synchronous task processing
5. **Single Worker Process** - Development server can't handle load
6. **No Connection Pooling** - Database connections per request
7. **No Rate Limiting** - No protection against abuse
8. **Blocking I/O for Email** - OTP sending blocks request

## Target Capacity
- **500 requests/min** = ~8.3 requests/sec
- **Peak Load**: ~15-20 requests/sec
- **Response Time Target**: < 200ms average
- **Concurrent Users**: ~50-100

## Implementation Plan

### Phase 1: Database Migration (High Priority)
**Current**: SQLite (file-based, not concurrent)
**Target**: PostgreSQL (production-grade, concurrent)

#### Steps:
1. Install PostgreSQL locally and on production
2. Update connection string in config
3. Migrate data from SQLite to PostgreSQL
4. Add connection pooling (psycopg2)
5. Implement query optimization

#### Benefits:
- ✅ Concurrent request support
- ✅ ACID compliance
- ✅ Better indexing support
- ✅ Row-level locking
- ✅ Replication support

### Phase 2: Application Server (High Priority)
**Current**: Flask development server (not for production)
**Target**: Gunicorn + Nginx

#### Steps:
1. Configure Gunicorn with multiple workers
2. Set up Nginx as reverse proxy
3. Implement graceful shutdown
4. Add health check endpoints
5. Load balancing across workers

#### Configuration:
```
Workers = CPU cores * 2 + 1
Worker Class: sync (for CPU-bound) or gevent (for I/O-bound)
Worker Timeout: 60 seconds
Max Requests: 1000 (to prevent memory leaks)
```

#### Benefits:
- ✅ Multiple concurrent requests
- ✅ Request distribution
- ✅ Zero-downtime deployments
- ✅ Better resource utilization

### Phase 3: Caching Layer (High Priority)
**Current**: None
**Target**: Redis cache

#### Implementation:
```python
# Session caching
# Query result caching
# Rate limiting storage
# Real-time data caching
```

#### What to Cache:
1. User sessions (Flask-Session + Redis)
2. Validation rules (5-min TTL)
3. App configuration (10-min TTL)
4. User authentication tokens (JWT)
5. Real-time event aggregations

#### Benefits:
- ✅ 80-90% faster responses for cached data
- ✅ Reduced database load
- ✅ Better user experience

### Phase 4: Asynchronous Task Processing (Medium Priority)
**Current**: Synchronous (blocks request)
**Target**: Celery + Redis queue

#### Tasks to Async:
1. Email sending (OTP, password reset)
2. Batch log processing
3. Report generation
4. Data export

#### Implementation:
```python
from celery import shared_task

@shared_task
def send_otp_async(email: str, otp: str):
    # Send email
    pass
```

#### Benefits:
- ✅ Non-blocking requests
- ✅ Retry logic for failed tasks
- ✅ Distributed task processing

### Phase 5: Database Optimization (Medium Priority)

#### Indexing Strategy:
```sql
-- Authentication
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_active ON users(is_active);

-- OTP management
CREATE INDEX idx_otp_email ON otps(email);
CREATE INDEX idx_otp_created ON otps(created_at);

-- Event logging
CREATE INDEX idx_log_app_date ON log_entries(app_id, created_at);
CREATE INDEX idx_log_event_name ON log_entries(event_name);

-- Validation
CREATE INDEX idx_rule_app ON validation_rules(app_id);
```

#### Query Optimization:
1. Use pagination for large result sets
2. Eager load relationships
3. Avoid N+1 queries
4. Use database-level aggregation

### Phase 6: API Rate Limiting (Medium Priority)
**Tool**: Flask-Limiter + Redis

#### Configuration:
```python
# Per IP rate limiting
- 100 requests per minute for auth endpoints
- 1000 requests per minute for API endpoints

# Per user rate limiting (authenticated)
- 200 requests per minute
```

#### Benefits:
- ✅ Protection against DDoS
- ✅ Fair resource allocation
- ✅ Abuse prevention

### Phase 7: Monitoring & Logging (Medium Priority)

#### Tools:
1. **Prometheus** - Metrics collection
2. **Grafana** - Visualization
3. **ELK Stack** - Log aggregation
4. **New Relic** or **Datadog** - APM

#### Key Metrics:
- Request rate (req/sec)
- Response time (p50, p95, p99)
- Error rate
- Database connection pool usage
- Cache hit ratio
- Worker utilization

### Phase 8: Load Balancing (Optional - For Horizontal Scaling)

#### Architecture:
```
              ┌─────────────────┐
              │   Nginx (L7)    │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼───┐   ┌────▼───┐   ┌────▼───┐
    │Gunicorn│   │Gunicorn│   │Gunicorn│
    │Server 1│   │Server 2│   │Server 3│
    └────┬───┘   └────┬───┘   └────┬───┘
         │             │             │
         └─────────────┼─────────────┘
                       │
              ┌────────▼────────┐
              │   PostgreSQL    │
              │    + Redis      │
              └─────────────────┘
```

## Implementation Order

### Week 1-2: Database Migration
- [ ] Install PostgreSQL
- [ ] Create migration scripts
- [ ] Test data migration
- [ ] Update database config
- [ ] Deploy to staging

### Week 2-3: Application Server
- [ ] Install Gunicorn
- [ ] Configure workers
- [ ] Set up Nginx
- [ ] Test under load
- [ ] Deploy to production

### Week 3-4: Caching Layer
- [ ] Install Redis
- [ ] Implement session caching
- [ ] Add query caching
- [ ] Configure TTLs
- [ ] Monitor cache performance

### Week 4-5: Async Tasks
- [ ] Install Celery
- [ ] Convert email tasks
- [ ] Set up task monitoring
- [ ] Implement retries
- [ ] Test failure scenarios

### Week 5-6: Optimization
- [ ] Add database indexes
- [ ] Optimize queries
- [ ] Implement pagination
- [ ] Add rate limiting
- [ ] Performance testing

### Week 6-7: Monitoring
- [ ] Set up Prometheus
- [ ] Configure Grafana
- [ ] Add application metrics
- [ ] Set up alerting
- [ ] Documentation

## Configuration Files Required

### PostgreSQL Setup
```bash
# Install
brew install postgresql  # macOS
sudo apt-get install postgresql  # Ubuntu

# Create database
createdb live_validation_dashboard
```

### Gunicorn Configuration (gunicorn_config.py)
```python
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Process naming
proc_name = 'live-validation-dashboard'

# Server mechanics
daemon = False
umask = 0

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
```

### Nginx Configuration (nginx.conf)
```nginx
upstream app_server {
    # Gunicorn servers
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name _;
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=general:10m rate=1000r/m;
    
    # Proxy settings
    location / {
        limit_req zone=general burst=20 nodelay;
        
        proxy_pass http://app_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check
    location /health {
        access_log off;
        proxy_pass http://app_server;
    }
}
```

### Redis Configuration (redis.conf)
```
# Memory limits
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# AOF
appendonly yes
appendfsync everysec

# Clients
maxclients 10000

# Network
timeout 300
tcp-backlog 511
```

## Performance Targets

| Metric | Current | Target |
|--------|---------|--------|
| Requests/min | ~100 | 500 |
| Response time (p50) | 500ms | <100ms |
| Response time (p95) | 2000ms | <300ms |
| Response time (p99) | 5000ms | <500ms |
| Concurrent users | 10 | 100 |
| Database connections | 1 | 50+ |
| Cache hit ratio | 0% | 70-80% |
| Error rate | 1% | <0.1% |

## Testing Plan

### Load Testing Script
```python
# Using locust or Apache JMeter
requests_per_second = 10  # ~500/min
duration_minutes = 5
concurrent_users = 50

test_scenarios = [
    {'endpoint': '/auth/login', 'weight': 20},
    {'endpoint': '/auth/register', 'weight': 10},
    {'endpoint': '/api/logs', 'weight': 40},
    {'endpoint': '/dashboard', 'weight': 30},
]
```

## Deployment Checklist

- [ ] PostgreSQL installed and configured
- [ ] Redis installed and running
- [ ] Gunicorn workers configured
- [ ] Nginx reverse proxy set up
- [ ] Database indexes created
- [ ] Connection pooling enabled
- [ ] Caching strategy implemented
- [ ] Rate limiting configured
- [ ] Health checks working
- [ ] Monitoring set up
- [ ] Load testing passed
- [ ] Documentation updated

## Expected Results

After full implementation:
- ✅ **500 requests/min easily handled**
- ✅ **Avg response time: 100-150ms**
- ✅ **99th percentile: <500ms**
- ✅ **0% failed requests under load**
- ✅ **70-80% cache hit ratio**
- ✅ **Horizontal scaling ready**

## Cost Implications

### Development
- Minimal (open-source tools only)

### Infrastructure
- PostgreSQL: $15-50/month (managed DB)
- Redis: $10-30/month (managed cache)
- Server upgrade: ~$30-100/month (for load capacity)

## Next Steps

1. **Review and approve** this plan
2. **Set up PostgreSQL** in staging
3. **Configure Gunicorn & Nginx**
4. **Implement caching layer**
5. **Run load tests** to validate
6. **Deploy to production** phase by phase


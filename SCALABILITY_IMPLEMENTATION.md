# Scalability Implementation - Phase 1 & 2 Setup

## Quick Start Guide

### Step 1: Install Required Services

#### PostgreSQL
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start

# Verify installation
psql --version
```

#### Redis
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo service redis-server start

# Verify installation
redis-cli ping  # Should return PONG
```

### Step 2: Database Migration from SQLite to PostgreSQL

```bash
# Create database
createdb live_validation_dashboard

# Create user (optional but recommended)
createuser dashboard_user
psql -U postgres -d live_validation_dashboard -c "ALTER USER dashboard_user WITH PASSWORD 'secure_password';"

# Check connection
psql -U dashboard_user -d live_validation_dashboard -h localhost
```

### Step 3: Update Flask Configuration

Update `config/config.py`:

```python
import os

class DevelopmentConfig:
    # PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://dashboard_user:secure_password@localhost:5432/live_validation_dashboard'
    )
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'echo_pool': False,
    }
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Session
    SESSION_TYPE = 'redis'
    SESSION_REDIS = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

class ProductionConfig(DevelopmentConfig):
    DEBUG = False
    TESTING = False
    
    # Use environment variables
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')
```

### Step 4: Update Requirements

Add to `requirements.txt`:

```
psycopg2-binary==2.9.9
redis==5.0.1
Flask-Session==0.5.0
Flask-Limiter==3.5.0
celery==5.3.4
```

Install:
```bash
pip install -r requirements.txt
```

### Step 5: Run Database Migration

```python
# Create migration script: migrate_sqlite_to_postgres.py
import sqlite3
import psycopg2
from datetime import datetime

def migrate_data():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('validation_dashboard.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        dbname='live_validation_dashboard',
        user='dashboard_user',
        password='secure_password',
        host='localhost',
        port=5432
    )
    pg_cursor = pg_conn.cursor()
    
    # Migrate tables
    tables = ['users', 'apps', 'validation_rules', 'log_entries', 'otps']
    
    for table in tables:
        # Get data from SQLite
        sqlite_cursor.execute(f'SELECT * FROM {table}')
        rows = sqlite_cursor.fetchall()
        
        # Insert into PostgreSQL
        if rows:
            columns = [description[0] for description in sqlite_cursor.description]
            for row in rows:
                placeholders = ','.join(['%s'] * len(row))
                insert_query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                try:
                    pg_cursor.execute(insert_query, row)
                except Exception as e:
                    print(f"Error migrating {table}: {e}")
        
        pg_conn.commit()
    
    print("Migration completed!")
    sqlite_conn.close()
    pg_conn.close()

if __name__ == '__main__':
    migrate_data()
```

Run migration:
```bash
python migrate_sqlite_to_postgres.py
```

### Step 6: Create Gunicorn Configuration

Create `gunicorn_config.py`:

```python
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = max(multiprocessing.cpu_count() * 2 + 1, 4)
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

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Environment
env = {
    'FLASK_ENV': os.getenv('FLASK_ENV', 'production'),
    'DATABASE_URL': os.getenv('DATABASE_URL'),
    'REDIS_URL': os.getenv('REDIS_URL'),
}

# Graceful timeout
graceful_timeout = 30

print(f"✅ Starting Gunicorn with {workers} workers")
```

### Step 7: Start Services

```bash
# Terminal 1: PostgreSQL (already running if you used brew services)
psql -U dashboard_user -d live_validation_dashboard

# Terminal 2: Redis (already running if you used brew services)
redis-cli

# Terminal 3: Gunicorn
gunicorn --config gunicorn_config.py "app:create_app()"

# Terminal 4: Nginx (optional, for local testing use Gunicorn directly)
# For production, use Nginx as reverse proxy
```

### Step 8: Verify Setup

```bash
# Check Gunicorn is running
curl http://127.0.0.1:8000/

# Check Redis
redis-cli ping  # Should return PONG

# Check PostgreSQL
psql -U dashboard_user -d live_validation_dashboard -c "SELECT COUNT(*) FROM users;"
```

## Testing the Setup

### Load Test Script

Create `test_scalability.py`:

```python
import requests
import time
import threading
from statistics import mean, stdev

BASE_URL = "http://127.0.0.1:8000"
results = []

def make_request(endpoint, method='GET', data=None):
    try:
        start = time.time()
        if method == 'POST':
            requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=10)
        else:
            requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        duration = (time.time() - start) * 1000  # Convert to ms
        results.append(duration)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def load_test(num_requests=100, concurrent=10):
    print(f"Starting load test: {num_requests} requests, {concurrent} concurrent")
    
    threads = []
    for i in range(num_requests):
        if i % concurrent == 0:
            # Start new batch
            time.sleep(0.1)
        
        # Test different endpoints
        endpoints = [
            ('/', 'GET'),
            ('/auth/login', 'GET'),
            ('/dashboard', 'GET'),
        ]
        endpoint, method = endpoints[i % len(endpoints)]
        
        t = threading.Thread(target=make_request, args=(endpoint, method))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Print results
    if results:
        print(f"\n📊 Load Test Results:")
        print(f"   Total Requests: {len(results)}")
        print(f"   Avg Response Time: {mean(results):.2f}ms")
        print(f"   Min Response Time: {min(results):.2f}ms")
        print(f"   Max Response Time: {max(results):.2f}ms")
        if len(results) > 1:
            print(f"   Std Dev: {stdev(results):.2f}ms")
        print(f"   Success Rate: {len(results)/num_requests*100:.1f}%")

if __name__ == '__main__':
    # Test with increasing load
    for num_requests in [50, 100, 200]:
        load_test(num_requests, concurrent=10)
        print()
```

Run:
```bash
python test_scalability.py
```

## Database Indexes

Create indexes for better performance:

```sql
-- Users
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_active ON users(is_active);

-- OTP
CREATE INDEX idx_otp_email ON otps(email);
CREATE INDEX idx_otp_expires ON otps(expires_at);
CREATE INDEX idx_otp_used ON otps(is_used);

-- Apps
CREATE INDEX idx_app_user ON apps(user_id);

-- Validation Rules
CREATE INDEX idx_rule_app ON validation_rules(app_id);

-- Log Entries
CREATE INDEX idx_log_app ON log_entries(app_id);
CREATE INDEX idx_log_date ON log_entries(created_at);
CREATE INDEX idx_log_event ON log_entries(event_name);

-- Composite indexes
CREATE INDEX idx_log_app_date ON log_entries(app_id, created_at DESC);
```

## Environment Variables

Create `.env`:

```bash
# Flask
FLASK_ENV=production
FLASK_APP=run.py

# Database
DATABASE_URL=postgresql://dashboard_user:secure_password@localhost:5432/live_validation_dashboard

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=app-password

# JWT
JWT_SECRET_KEY=your-secret-key-here

# App
APP_URL=http://localhost:5001
DEBUG=False
```

## Performance Monitoring

### Check Connection Pool Status

```python
# In your Flask app
from flask import jsonify

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'db_pool_size': db.engine.pool.checkedout(),
        'db_pool_overflow': db.engine.pool.overflow(),
        'timestamp': datetime.utcnow().isoformat()
    })
```

## Troubleshooting

### Issue: "SQLALCHEMY_DATABASE_URI not configured"
**Solution**: Ensure DATABASE_URL environment variable is set

### Issue: "Redis connection refused"
**Solution**: Check Redis is running: `redis-cli ping`

### Issue: "Database is locked" (SQLite)
**Solution**: This is why we're migrating to PostgreSQL!

### Issue: "Gunicorn workers not starting"
**Solution**: Check port 8000 is available: `lsof -i :8000`

## Next Steps

1. ✅ Install PostgreSQL and Redis
2. ✅ Migrate data from SQLite
3. ✅ Update Flask configuration
4. ✅ Create database indexes
5. ✅ Set up Gunicorn with multiple workers
6. ✅ Configure Nginx (for production)
7. ✅ Run load tests
8. ✅ Monitor performance

After completing these steps, your application should easily handle 500 requests/min!


#!/usr/bin/env python
"""
Gunicorn configuration for production deployment
Handles multiple worker processes for concurrent request handling
"""

import multiprocessing
import os
from pathlib import Path

# Determine number of workers (CPU cores * 2 + 1), override with WEB_CONCURRENCY if set
# For 500 req/min (8.3 req/sec avg), we recommend 4-8 workers minimum
cpu_count = multiprocessing.cpu_count()
default_workers = max(cpu_count * 2 + 1, 4)
workers = int(os.getenv('WEB_CONCURRENCY', default_workers))
workers = max(workers, 1)

# Server socket
bind = os.getenv('GUNICORN_BIND', '127.0.0.1:8000')
backlog = 2048

# Worker processes
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', '1000'))
timeout = int(os.getenv('GUNICORN_TIMEOUT', '60'))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '5'))

# Max requests per worker (for memory leak prevention)
max_requests = 1000
max_requests_jitter = 100

# Process naming
proc_name = 'live-validation-dashboard'

# Daemon mode (set to False for Docker containers)
daemon = False

# Logging
accesslog = os.getenv('GUNICORN_ACCESSLOG', '-')
errorlog = os.getenv('GUNICORN_ERRORLOG', '-')
loglevel = os.getenv('GUNICORN_LOGLEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Graceful timeout for SIGTERM
graceful_timeout = 30

# Server mechanics
# Server socket keep-alive timeout
keepalive = 5

# Health check
preload_app = False

# When to reload workers (disabled for now, use deployment strategy instead)
reload = False

# Custom settings for Flask
env = {
    'FLASK_ENV': os.getenv('FLASK_ENV', 'production'),
    'PYTHONUNBUFFERED': '1',
}

# Hooks
def on_starting(server):
    """Called just before Gunicorn starts"""
    print(f"""
    ╭────────────────────────────────────────────────────────────╮
    │  Live Validation Dashboard - Gunicorn Server              │
    │────────────────────────────────────────────────────────────│
    │  Workers: {workers:2d}
    │  Worker Class: {worker_class}
    │  Bind: {bind}
    │  Timeout: {timeout}s
    │  Max Requests: {max_requests}
    │  CPU Cores: {cpu_count}
    ╰────────────────────────────────────────────────────────────╯
    """)

def on_exit(server):
    """Called just after Gunicorn exits"""
    print("\n✅ Gunicorn server shutdown complete\n")

def when_ready(server):
    """Called when Gunicorn is ready to accept requests"""
    print(f"\n✅ Gunicorn is ready. Spawning {workers} workers\n")

def worker_int(worker):
    """Called on SIGINT or SIGQUIT of a worker"""
    print(f"⚠️  Worker {worker.pid} handling SIGINT/SIGQUIT")

def worker_abort(worker):
    """Called on SIGABRT of a worker"""
    print(f"❌ Worker {worker.pid} received SIGABRT")

# Connection pooling settings for better performance
# If using a connection pool, these are good defaults:
# - pool_size: Number of permanent connections to keep
# - pool_recycle: Recycle connections after N seconds (1 hour = 3600)
# - pool_pre_ping: Test connections before using them
# - echo_pool: Log pool events (development only)

# Workers should be killed and restarted periodically
# max_requests = 1000 means each worker handles 1000 requests before respawn
# This prevents memory leaks and ensures fresh connections

# For 500 req/min (8.3 req/sec):
# - 4 workers × ~100 req/worker/min = 400 req/min capacity (conservative)
# - 4 workers × ~200 req/worker/min = 800 req/min capacity (realistic)
# So 4 workers is sufficient, but we're setting to cpu_count*2+1 for headroom

print(f"\n🚀 Gunicorn Server Configuration")
print(f"   Workers: {workers}")
print(f"   Worker Class: {worker_class}")
print(f"   Bind Address: {bind}")
print(f"   Timeout: {timeout}s")
print(f"   Max Requests/Worker: {max_requests}")
print(f"   CPU Cores Detected: {cpu_count}\n")

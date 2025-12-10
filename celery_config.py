"""Celery configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

# Celery broker (message queue) - using Redis
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/1')

# Task configuration
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task timeouts
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes

# Task routing - direct tasks to specific queues
CELERY_TASK_ROUTES = {
    'app.tasks.process_event_async': {'queue': 'default'},
    'app.tasks.send_email_async': {'queue': 'emails'},
    'app.tasks.batch_process_events': {'queue': 'batch_processing'},
}

# Task retry configuration
CELERY_TASK_AUTORETRY_FOR = (Exception,)
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 1 minute

# Worker settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Result backend settings
CELERY_RESULT_EXPIRES = 3600  # Results kept for 1 hour
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'master_name': 'mymaster'
}

print("✅ Celery configuration loaded")
print(f"   Broker: {CELERY_BROKER_URL}")
print(f"   Backend: {CELERY_RESULT_BACKEND}")

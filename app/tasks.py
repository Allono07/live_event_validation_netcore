"""Celery tasks for asynchronous processing."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file BEFORE any other imports
# Use explicit path to ensure it works regardless of working directory
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from celery import Celery, shared_task
from flask import current_app
from app.models.log_entry import LogEntry
from app.models.app import App
from config.database import db
import json
import hashlib
from datetime import datetime

# Initialize Celery with Redis broker from environment
celery = Celery(__name__)
celery.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


def init_celery(app):
    """Initialize Celery with Flask app context."""
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery


@shared_task
def process_event_async(app_id: str, event_name: str, payload: dict, 
                       validation_status: str, validation_results: dict = None):
    """
    Asynchronously process and store event in database.
    
    Called from API endpoint after validation completes.
    Event is queued in Redis and processed by Celery worker.
    
    Args:
        app_id: Application ID (string, e.g., "aj12")
        event_name: Name of the event
        payload: Event payload (dict)
        validation_status: 'valid', 'invalid', or 'error'
        validation_results: Detailed validation results
    
    Returns:
        dict with status and log_entry_id
    """
    # Load .env inside task (forked worker process may not have it)
    from pathlib import Path
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env'
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Create Flask app context for database access
    from app import create_app
    flask_app = create_app('development')
    
    with flask_app.app_context():
        # Debug: Print database URI
        db_uri = flask_app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')
        print(f"🔧 Database URI: {db_uri[:50]}...")
        
        try:
            # Look up the App record to get the integer primary key
            app_record = App.query.filter_by(app_id=app_id).first()
            if not app_record:
                print(f"❌ App not found for app_id: {app_id}")
                return {
                    'status': 'error',
                    'message': f'App not found for app_id: {app_id}'
                }
            
            # Calculate payload hash for deduplication
            payload_json = json.dumps(payload, sort_keys=True)
            payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
            
            # Create log entry using the integer primary key
            log_entry = LogEntry(
                app_id=app_record.id,  # Use integer primary key
                event_name=event_name,
                payload=payload,
                payload_hash=payload_hash,
                validation_status=validation_status,
                validation_results=validation_results,
                created_at=datetime.utcnow()
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
            # Timestamp-based deduplication: delete older entries with same app_id + event_name
            # This keeps only the LATEST entry per event_name (for dashboard display)
            deleted_count = LogEntry.query.filter(
                LogEntry.app_id == app_record.id,
                LogEntry.event_name == event_name,
                LogEntry.id != log_entry.id  # Keep the new entry
            ).delete(synchronize_session=False)
            
            if deleted_count > 0:
                db.session.commit()
                print(f"🗑️  Deduplication: removed {deleted_count} older '{event_name}' entries")
            
            print(f"✅ Event stored async: {event_name} (ID: {log_entry.id}) - Status: {validation_status}")
            
            return {
                'status': 'success',
                'log_entry_id': log_entry.id,
                'message': f'Event stored with ID {log_entry.id}',
                'duplicates_removed': deleted_count
            }
        except Exception as e:
            print(f"❌ Error processing event async: {str(e)}")
            db.session.rollback()
            return {
                'status': 'error',
                'message': f'Failed to store event: {str(e)}'
            }


@shared_task
def send_email_async(email: str, subject: str, html_body: str):
    """
    Asynchronously send email.
    
    Args:
        email: Recipient email
        subject: Email subject
        html_body: HTML email body
    
    Returns:
        dict with status
    """
    from app import create_app
    app = create_app('development')
    
    with app.app_context():
        try:
            from flask_mail import Mail, Message
            from app.utils.email_utils import mail
            
            msg = Message(
                subject=subject,
                recipients=[email],
                html=html_body
            )
            mail.send(msg)
            
            print(f"✅ Email sent async to {email}")
            return {'status': 'success', 'message': f'Email sent to {email}'}
        except Exception as e:
            print(f"❌ Error sending email async: {str(e)}")
            return {'status': 'error', 'message': str(e)}


@shared_task
def batch_process_events(app_id: int, hours: int = 24):
    """
    Asynchronously batch process events for aggregation/reporting.
    
    Args:
        app_id: Application ID
        hours: Number of hours to look back
    
    Returns:
        dict with processing results
    """
    from app import create_app
    app = create_app('development')
    
    with app.app_context():
        try:
            from datetime import timedelta
            from sqlalchemy import func
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Aggregate stats
            stats = db.session.query(
                LogEntry.validation_status,
                func.count(LogEntry.id).label('count')
            ).filter(
                LogEntry.app_id == app_id,
                LogEntry.created_at >= cutoff_time
            ).group_by(LogEntry.validation_status).all()
            
            print(f"✅ Batch processing complete for app {app_id}")
            
            return {
                'status': 'success',
                'app_id': app_id,
                'stats': {s[0]: s[1] for s in stats}
            }
        except Exception as e:
            print(f"❌ Error batch processing: {str(e)}")
            return {'status': 'error', 'message': str(e)}

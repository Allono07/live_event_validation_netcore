"""API controller for receiving logs from mobile apps."""
from flask import Blueprint, request, jsonify
from app.services.log_service import LogService
from app.services.app_service import AppService
from app import socketio
from app.tasks import process_event_async
import logging
import json
from datetime import datetime

api_bp = Blueprint('api', __name__)
log_service = LogService()
app_service = AppService()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Also create a file handler for API logs
file_handler = logging.FileHandler('api_logs.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)


@api_bp.route('/logs/<app_id>', methods=['POST'])
def receive_log(app_id):
    """Receive log from mobile app.
    
    Accepts either:
    1. Single JSON object
    2. Plain text with multiple "Event Payload: {...}" lines
    """
    try:
        # Check if app exists; return 444 if not
        app = app_service.get_app_by_id(app_id)
        if not app:
            logger.warning(f"Received request for non-existent app_id: {app_id}")
            return jsonify({'error': 'App not found'}), 444

        content_type = request.content_type
        
        # Log incoming request
        logger.info(f"=== INCOMING LOG REQUEST ===")
        logger.info(f"App ID: {app_id}")
        logger.info(f"IP Address: {request.remote_addr}")
        logger.info(f"Timestamp: {datetime.now()}")
        logger.info(f"Content-Type: {content_type}")
        
        events_to_process = []
        
        # Check if it's plain text or JSON
        if content_type and 'text/plain' in content_type:
            # Handle plain text format with multiple events
            raw_text = request.get_data(as_text=True)
            logger.info(f"Raw Text Data: {raw_text}")
            
            # Split by "Event Payload:" and process each
            lines = raw_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Event Payload:'):
                    # Extract JSON part after "Event Payload:"
                    json_str = line.replace('Event Payload:', '').strip()
                    try:
                        event_data = json.loads(json_str)
                        events_to_process.append(event_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from line: {line}, error: {e}")
                        continue
        else:
            # Handle JSON format
            log_data = request.get_json()
            logger.info(f"JSON Data: {log_data}")
            
            if not log_data:
                logger.warning(f"Invalid JSON received for app_id: {app_id}")
                return jsonify({'error': 'Invalid JSON'}), 400
            
            events_to_process.append(log_data)
        
        if not events_to_process:
            logger.warning(f"No valid events found in request for app_id: {app_id}")
            return jsonify({'error': 'No valid events found'}), 400
        
        logger.info(f"Processing {len(events_to_process)} events")
        
        results = []
        
        # Process each event
        for event_data in events_to_process:
            event_name = event_data.get('eventName')
            if not event_name:
                logger.warning(f"Missing eventName in payload for app_id: {app_id}")
                results.append({'error': 'Missing eventName', 'data': event_data})
                continue
            
            # Use the payload directly as-is (no transformation)
            # Just wrap it in our expected format
            formatted_data = {
                'event_name': event_name,
                'payload': event_data  # Keep all fields including eventName
            }
            
            logger.info(f"Processing event: {event_name}")
            
            # Validate the event first (synchronous - fast)
            success, validation_result = log_service.validate_log(app_id, formatted_data)
            
            # Check if app not found - return 404 immediately
            if not success and validation_result.get('error') == 'App not found':
                logger.warning(f"App not found for app_id: {app_id}")
                return jsonify({'error': 'App not found'}), 404
            
            # Queue event storage to Celery (async - non-blocking)
            if success:
                validation_status = 'valid'
                logger.info(f"✅ Validation PASSED for app_id: {app_id}, event: {event_name}")
            else:
                validation_status = 'invalid'
                logger.warning(f"⚠️  Validation FAILED for app_id: {app_id}, event: {event_name}")
            
            # Queue async task to store in database
            task = process_event_async.delay(
                app_id=app_id,
                event_name=event_name,
                payload=event_data,
                validation_status=validation_status,
                validation_results=validation_result.get('details')
            )
            
            # Return immediately (202 Accepted) - don't wait for database write
            results.append({
                'event_name': event_name,
                'status': validation_status,
                'task_id': task.id,
                'message': 'Event queued for processing'
            })
            
            # Emit real-time update via WebSocket
            socketio.emit('validation_update', {
                'app_id': app_id,
                'event': event_name,
                'status': validation_status
            }, room=app_id)
        
        logger.info(f"===========================")
        
        # Return 202 Accepted - event queued for async processing
        if len(results) == 1:
            return jsonify(results[0]), 202
        else:
            return jsonify({'processed': len(results), 'results': results}), 202
            
    except Exception as e:
        logger.error(f"ERROR processing log for app_id: {app_id}, error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'validation-api'}), 200

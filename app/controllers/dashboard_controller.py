"""Dashboard controller."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import csv
import io
import json
from app.services.app_service import AppService
from app.services.validation_service import ValidationService
from app.services.log_service import LogService
from config.database import db

dashboard_bp = Blueprint('dashboard', __name__)
app_service = AppService()
validation_service = ValidationService()
log_service = LogService()


@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard page."""
    apps = app_service.get_user_apps(current_user.id)
    return render_template('dashboard.html', apps=apps)


@dashboard_bp.route('/app/<app_id>')
@login_required
def app_detail(app_id):
    """App detail page with live validation."""
    # Check if user owns this app
    if not app_service.user_owns_app(current_user.id, app_id):
        flash('Access denied', 'error')
        return redirect(url_for('dashboard.index'))
    
    app = app_service.get_app_by_id(app_id)
    if not app:
        flash('App not found', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Get validation stats
    stats = log_service.get_validation_stats(app_id, hours=24)
    
    # Get recent logs
    recent_logs = log_service.get_recent_logs(app_id, hours=24, limit=100)
    
    # Get event names
    event_names = validation_service.get_event_names(app_id)
    
    # Check if has validation rules
    has_rules = validation_service.has_validation_rules(app_id)
    
    return render_template('app_detail.html',
                         app=app,
                         stats=stats,
                         recent_logs=recent_logs,
                         event_names=event_names,
                         has_rules=has_rules)


@dashboard_bp.route('/create-app', methods=['POST'])
@login_required
def create_app():
    """Create a new application."""
    name = request.form.get('name')
    description = request.form.get('description', '')
    app_id = request.form.get('app_id', '').strip()  # Manual App ID input
    
    if not name:
        flash('App name is required', 'danger')
        return redirect(url_for('dashboard.index'))
    
    success, result = app_service.create_app(
        name=name,
        description=description,
        user_id=current_user.id,
        app_id=app_id if app_id else None  # Use manual ID if provided
    )
    
    if success:
        flash(f'App "{name}" created successfully!', 'success')
    else:
        flash(f'Error creating app: {result}', 'danger')
    
    return redirect(url_for('dashboard.index'))
@dashboard_bp.route('/app/<app_id>/upload-rules', methods=['POST'])
@login_required
def upload_rules(app_id):
    """Upload validation rules CSV."""
    # Check if user owns this app
    if not app_service.user_owns_app(current_user.id, app_id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if 'csv_file' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('dashboard.app_detail', app_id=app_id))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('dashboard.app_detail', app_id=app_id))
    
    if not file.filename.endswith('.csv'):
        flash('File must be CSV', 'danger')
        return redirect(url_for('dashboard.app_detail', app_id=app_id))
    
    try:
        # Read CSV content
        csv_content = file.read().decode('utf-8')
        
        # Upload and save rules
        result = validation_service.upload_validation_rules(app_id, csv_content)
        
        if result['success']:
            flash(f"Validation rules uploaded: {result['rules_count']} rules", 'success')
            return redirect(url_for('dashboard.app_detail', app_id=app_id))
        else:
            flash(f"Error: {result['error']}", 'danger')
            return redirect(url_for('dashboard.app_detail', app_id=app_id))
            
    except Exception as e:
        flash(f"Error uploading CSV: {str(e)}", 'danger')
        return redirect(url_for('dashboard.app_detail', app_id=app_id))


@dashboard_bp.route('/app/<app_id>/stats', methods=['GET'])
@login_required
def get_stats(app_id):
    """Get validation statistics (AJAX endpoint)."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    hours = request.args.get('hours', 24, type=int)
    stats = log_service.get_validation_stats(app_id, hours)
    return jsonify(stats)


@dashboard_bp.route('/app/<app_id>/logs')
@login_required
def get_logs(app_id):
    """Get paginated logs (AJAX endpoint).
    
    Query parameters:
    - page: Page number (1-indexed, default 1)
    - limit: Results per page (default 50)
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    # Get app to get internal app_id
    app = app_service.get_app_by_id(app_id)
    if not app:
        return jsonify({'error': 'App not found'}), 404
    
    # Get paginated logs
    logs, total = log_service.get_app_logs_paginated(app_id, page, limit)
    
    return jsonify({
        'logs': [log.to_dict() for log in logs],
        'total': total,
        'page': page,
        'limit': limit
    })


@dashboard_bp.route('/app/<app_id>/coverage', methods=['GET'])
@login_required
def get_coverage(app_id):
    """Get event coverage comparison (AJAX endpoint).
    
    Returns:
    - captured: count of events from validation rules that have been captured in logs
    - missing: count of events in validation rules that have NOT been captured yet
    - total: total count of events in validation rules
    - missing_events: list of event names in rules but not captured
    - event_names: list of all events in rules
    
    Note: Coverage only considers events that are defined in validation rules.
    Custom events not in rules are not counted in coverage.
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get event names from validation rules (sheet) - this is our baseline
        app = app_service.get_app_by_id(app_id)
        if not app:
            return jsonify({'error': 'App not found'}), 404
        
        sheet_event_names = validation_service.get_event_names(app_id)
        sheet_event_names_set = set(sheet_event_names)
        
        # Get event names from captured logs
        captured_event_names = log_service.get_distinct_event_names(app_id)
        captured_event_names_set = set(captured_event_names)
        
        # Calculate coverage ONLY for events in the rules
        # captured = events in rules AND in logs
        captured_from_rules_set = sheet_event_names_set & captured_event_names_set
        captured_count = len(captured_from_rules_set)
        
        # total = all events in rules
        total_count = len(sheet_event_names_set)
        
        # missing = events in rules BUT NOT in logs
        missing_events_set = sheet_event_names_set - captured_event_names_set
        missing_count = len(missing_events_set)
        
        # Validate: captured + missing should equal total
        # If not, there's a data consistency issue
        if captured_count + missing_count != total_count:
            print(f"WARNING: Coverage math error! captured({captured_count}) + missing({missing_count}) != total({total_count})")
        
        return jsonify({
            'captured': captured_count,
            'missing': missing_count,
            'total': total_count,
            'missing_events': sorted(list(missing_events_set)),
            'event_names': sheet_event_names
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/event-names', methods=['GET'])
@login_required
def get_event_names(app_id):
    """Get all distinct event names from logs (AJAX endpoint)."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        event_names = log_service.get_distinct_event_names(app_id)
        return jsonify({'event_names': event_names})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/fully-valid-events', methods=['GET'])
@login_required
def get_fully_valid_events(app_id):
    """Get list of events where the latest instance has all valid fields (AJAX endpoint)."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        fully_valid_events = log_service.get_fully_valid_events(app_id, hours=24)
        return jsonify({'fully_valid_events': fully_valid_events})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/filter-logs', methods=['POST'])
@login_required
def filter_logs_database(app_id):
    """Filter logs against entire database with specified criteria.
    
    This endpoint queries the database directly instead of filtering client-side cached results.
    
    Accepts JSON body with keys:
    - event_names: list of event names to filter by (optional)
    - field_names: list of field names to filter by (optional)
    - validation_statuses: list of validation statuses to filter by (optional)
    - expected_types: list of expected types to filter by (optional)
    - received_types: list of received types to filter by (optional)
    - value_search: string to search for in payload values (optional, case-insensitive)
    
    Returns: List of filtered validation result dicts
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json() or {}
        
        # Build filter dict
        filters = {}
        if data.get('event_names'):
            filters['event_names'] = data['event_names']
        if data.get('field_names'):
            filters['field_names'] = data['field_names']
        if data.get('validation_statuses'):
            filters['validation_statuses'] = data['validation_statuses']
        if data.get('expected_types'):
            filters['expected_types'] = data['expected_types']
        if data.get('received_types'):
            filters['received_types'] = data['received_types']
        if data.get('value_search'):
            filters['value_search'] = data['value_search']
        
        # Query database
        results = log_service.filter_logs(app_id, filters)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/filter', methods=['POST', 'OPTIONS'])
@login_required
def filter_results(app_id):
    """Filter results sent from client (simple server-side filter helper).

    Accepts JSON body with keys:
    - results: list of result dicts
    - filters: dict of field -> list of accepted values
    - sort_by: optional field
    - sort_order: 'asc' or 'desc'
    - date_range: optional dict with 'start' and 'end' in ISO format
    - search_term: optional string
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403

    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json() or {}
        results = data.get('results', [])
        filters = data.get('filters', {}) or {}
        sort_by = data.get('sort_by')
        sort_order = data.get('sort_order', 'asc')
        date_range = data.get('date_range') or {}
        search_term = (data.get('search_term') or '').lower()

        filtered = results

        # Apply filters (simple equality membership)
        if filters:
            for field, values in filters.items():
                if not values:
                    continue
                if field == 'search_term':
                    filtered = [r for r in filtered if any(search_term in str(v).lower() for v in r.values())]
                else:
                    vals_lower = [str(v).lower() for v in values]
                    filtered = [r for r in filtered if str(r.get(field, '')).lower() in vals_lower]

        # Apply date range filter on timestamp if requested
        if date_range and date_range.get('start') and date_range.get('end'):
            from datetime import datetime
            start = datetime.fromisoformat(date_range['start'])
            end = datetime.fromisoformat(date_range['end'])
            def in_range(r):
                try:
                    val = r.get('value')
                    if not val:
                        return False
                    dt = datetime.fromisoformat(str(val))
                    return start <= dt <= end
                except Exception:
                    return False
            filtered = [r for r in filtered if in_range(r)]

        # Sorting
        if sort_by:
            reverse = (sort_order == 'desc')
            try:
                filtered = sorted(filtered, key=lambda x: str(x.get(sort_by, '')).lower(), reverse=reverse)
            except Exception:
                pass

        return jsonify(filtered)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/download-report', methods=['POST'])
@login_required
def download_validation_report(app_id):
    """Download validation results as CSV.
    
    Expects JSON body with:
    - results: List of validation results to download
    
    Returns CSV with columns:
    - eventName, key, value, expectedType, receivedType, validationStatus, comment
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        # Create CSV content
        output = io.StringIO()
        fieldnames = ['eventName', 'key', 'value', 'expectedType', 'receivedType', 'validationStatus', 'comment']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Add comments to results if not present
        for result in results:
            clean_result = {
                'eventName': result.get('eventName', ''),
                'key': result.get('key', ''),
                'value': result.get('value', ''),
                'expectedType': result.get('expectedType', ''),
                'receivedType': result.get('receivedType', ''),
                'validationStatus': result.get('validationStatus', ''),
                'comment': result.get('comment', '')
            }
            
            # Add comment if not present
            if not clean_result['comment']:
                status = clean_result['validationStatus']
                if status == 'Valid':
                    clean_result['comment'] = 'Field validation passed'
                elif status == 'Invalid/Wrong datatype/value':
                    clean_result['comment'] = f"Expected type: {clean_result['expectedType']}, Received type: {clean_result['receivedType']}"
                elif status == 'Payload value is Empty':
                    clean_result['comment'] = 'Field value is empty or null'
                elif status == 'Extra key present in the log':
                    clean_result['comment'] = 'This is an EXTRA payload or there is a spelling mistake with the required payload'
                elif status == 'Payload not present in the log':
                    clean_result['comment'] = 'Field is missing in the payload'
                else:
                    clean_result['comment'] = status
            
            writer.writerow(clean_result)
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=validation_results_{app_id}.csv',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/download-valid-events', methods=['POST'])
@login_required
def download_valid_events(app_id):
    """Download validation summary report as CSV.
    
    Returns CSV with one row per unique user event (eventId=0) showing:
    - Event Name
    - Latest Timestamp
    - Field Name
    - Value
    - Expected Type
    - Received Type
    - Validation Status (detailed message)
    - Latest Log Payload (full JSON)
    
    Only shows the most recent instance of each user event.
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get app
        app = app_service.get_app_by_id(app_id)
        if not app:
            return jsonify({'error': 'App not found'}), 404
        
        # Get recent logs (last 24 hours)
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(hours=24)
        
        from app.repositories.log_repository import LogRepository
        log_repo = LogRepository()
        
        # Get all logs ordered by newest first
        logs = db.session.query(log_repo.model).filter(
            log_repo.model.app_id == app.id,
            log_repo.model.created_at >= since
        ).order_by(log_repo.model.created_at.desc()).all()
        
        # Track latest instance of each event
        event_summary = {}  # event_name -> log entry
        
        for log in logs:
            event_name = log.event_name
            
            # Skip if we already have this event (we want the latest only)
            if event_name in event_summary:
                continue
            
            # Check if this is a user event (eventId = 0)
            # Default to True (assume user event unless proven otherwise)
            is_user_event = True
            
            # Check validation_results for eventId
            if log.validation_results and isinstance(log.validation_results, list):
                for result in log.validation_results:
                    if result.get('key', '').lower() == 'eventid':
                        event_id = result.get('value')
                        # If eventId is not 0, it's a system event
                        if event_id != 0 and event_id != '0':
                            is_user_event = False
                        break
            
            # Also check payload as backup
            if log.payload and isinstance(log.payload, dict):
                event_id = log.payload.get('eventId') or log.payload.get('eventid')
                if event_id is not None and event_id != 0 and event_id != '0':
                    is_user_event = False
            
            # Skip non-user events
            if not is_user_event:
                continue
            
            # Store the latest user event
            event_summary[event_name] = log
        
        # Create CSV content
        output = io.StringIO()
        fieldnames = ['Event Name', 'Latest Timestamp', 'Field Name', 'Value', 'Expected Type', 'Received Type', 'Validation Status', 'Latest Log Payload']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write rows for each event
        for event_name in sorted(event_summary.keys()):
            log = event_summary[event_name]
            timestamp = log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else ''
            payload_json = json.dumps(log.payload) if log.payload else '{}'
            
            # Get validation results
            if log.validation_results and isinstance(log.validation_results, list):
                for idx, result in enumerate(log.validation_results):
                    writer.writerow({
                        'Event Name': event_name if idx == 0 else '',  # Only show event name on first row
                        'Latest Timestamp': timestamp if idx == 0 else '',
                        'Field Name': result.get('key', ''),
                        'Value': result.get('value', ''),
                        'Expected Type': result.get('expectedType', ''),
                        'Received Type': result.get('receivedType', ''),
                        'Validation Status': result.get('validationStatus', ''),
                        'Latest Log Payload': payload_json if idx == 0 else ''  # Only show payload on first row
                    })
            else:
                # No validation results, write one row with event info
                writer.writerow({
                    'Event Name': event_name,
                    'Latest Timestamp': timestamp,
                    'Field Name': '',
                    'Value': '',
                    'Expected Type': '',
                    'Received Type': '',
                    'Validation Status': log.validation_status or '',
                    'Latest Log Payload': payload_json
                })
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=validation_summary_{app_id}.csv',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/delete-logs', methods=['POST'])
@login_required
def delete_all_logs(app_id):
    """Delete all stored logs for the given app.

    This endpoint is protected and requires the current user to own the app.
    Returns JSON: { success: true, deleted: count }
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403

    success, deleted = log_service.delete_all_logs(app_id)
    if not success:
        return jsonify({'error': 'App not found'}), 404

    return jsonify({'success': True, 'deleted': deleted})

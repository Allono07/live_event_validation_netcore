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

    # For each app compute the number of distinct custom events defined in the validation rules (CSV/sheet)
    # i.e., count of unique event names present in the uploaded rules
    custom_event_counts = {}
    for a in apps:
        try:
            rule_event_names = validation_service.get_event_names(a.app_id)
            custom_event_counts[a.app_id] = len(set(rule_event_names))
        except Exception:
            custom_event_counts[a.app_id] = 0

    return render_template('dashboard.html', apps=apps, custom_event_counts=custom_event_counts)


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
    platform = request.form.get('platform', 'android')
    sdk_type = request.form.get('sdk_type', 'ce')
    
    if not name:
        flash('App name is required', 'danger')
        return redirect(url_for('dashboard.index'))
    
    success, result = app_service.create_app(
        name=name,
        description=description,
        user_id=current_user.id,
        app_id=app_id if app_id else None,  # Use manual ID if provided
        platform=platform,
        sdk_type=sdk_type
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


@dashboard_bp.route('/app/<app_id>/download-all-results', methods=['POST'])
@login_required
def download_all_results(app_id):
    """Download validation results for ALL unique latest events as CSV.
    
    This endpoint exports all latest unique events from the database,
    with optional filters applied.
    
    Expects JSON body with optional:
    - filters: Dict with filter criteria (event_names, field_names, validation_statuses, etc.)
    
    Returns CSV with columns:
    - eventName, key, value, expectedType, receivedType, validationStatus, comment
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get app
        app = app_service.get_app_by_id(app_id)
        if not app:
            return jsonify({'error': 'App not found'}), 404
        
        # Get filters from request body
        data = request.get_json() or {}
        filters = data.get('filters', {})
        
        # Get all latest unique events from database
        from app.repositories.log_repository import LogRepository
        log_repo = LogRepository()
        
        all_results = log_repo.get_all_latest_unique_events(app.id)
        
        # Apply filters if provided
        if filters:
            filtered_results = []
            
            for result in all_results:
                # Check event_names filter
                if 'event_names' in filters and filters['event_names']:
                    if result['eventName'] not in filters['event_names']:
                        continue
                
                # Check field_names filter
                if 'field_names' in filters and filters['field_names']:
                    if result['key'] not in filters['field_names']:
                        continue
                
                # Check validation_statuses filter
                if 'validation_statuses' in filters and filters['validation_statuses']:
                    if result['validationStatus'] not in filters['validation_statuses']:
                        continue
                
                # Check expected_types filter
                if 'expected_types' in filters and filters['expected_types']:
                    if result['expectedType'] not in filters['expected_types']:
                        continue
                
                # Check received_types filter
                if 'received_types' in filters and filters['received_types']:
                    if result['receivedType'] not in filters['received_types']:
                        continue
                
                # Check value_search filter (case-insensitive substring match)
                if 'value_search' in filters and filters['value_search']:
                    search_term = str(filters['value_search']).lower()
                    if search_term not in str(result['value']).lower():
                        continue
                
                filtered_results.append(result)
            
            all_results = filtered_results
        
        if not all_results:
            return jsonify({'error': 'No events found matching filters'}), 404
        
        # Create CSV content
        output = io.StringIO()
        fieldnames = ['eventName', 'key', 'value', 'expectedType', 'receivedType', 'validationStatus', 'comment']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Add comments to results
        for result in all_results:
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
                'Content-Disposition': f'attachment; filename=validation_results_all_{app_id}.csv',
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


@dashboard_bp.route('/app/<app_id>', methods=['DELETE'])
@login_required
def delete_app(app_id):
    """Delete an application and all its associated data.
    
    This will delete:
    - The application itself
    - All validation rules for this app
    - All logs/events for this app
    
    Returns JSON: { success: true } or { success: false, error: "message" }
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    success, error = app_service.delete_app(app_id)
    if not success:
        return jsonify({'success': False, 'error': error or 'App not found'}), 404

    flash('Application deleted successfully', 'success')
    return jsonify({'success': True})


# ====================== VALIDATION RULES CRUD ENDPOINTS ======================

@dashboard_bp.route('/app/<app_id>/validation-rules', methods=['GET'])
@login_required
def get_validation_rules(app_id):
    """Get all validation rules for an app."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        app = app_service.get_app_by_id(app_id)
        if not app:
            return jsonify({'error': 'App not found'}), 404
        
        from app.repositories.validation_rule_repository import ValidationRuleRepository
        rule_repo = ValidationRuleRepository()
        rules = rule_repo.get_by_app(app.id)
        
        return jsonify({
            'success': True,
            'rules': [rule.to_dict() for rule in rules]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/validation-rules', methods=['POST'])
@login_required
def create_validation_rule(app_id):
    """Create a new validation rule."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        app = app_service.get_app_by_id(app_id)
        if not app:
            return jsonify({'error': 'App not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['event_name', 'field_name', 'data_type']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        from app.repositories.validation_rule_repository import ValidationRuleRepository
        rule_repo = ValidationRuleRepository()
        
        rule = rule_repo.create(
            app_id=app.id,
            event_name=data['event_name'].lower(),
            field_name=data['field_name'],
            data_type=data['data_type'],
            is_required=data.get('is_required', False),
            expected_pattern=data.get('expected_pattern'),
            condition=data.get('condition')
        )
        
        return jsonify({
            'success': True,
            'rule': rule.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/validation-rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_validation_rule(app_id, rule_id):
    """Update an existing validation rule."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        app = app_service.get_app_by_id(app_id)
        if not app:
            return jsonify({'error': 'App not found'}), 404
        
        from app.repositories.validation_rule_repository import ValidationRuleRepository
        rule_repo = ValidationRuleRepository()
        
        rule = rule_repo.get_by_id(rule_id)
        if not rule or rule.app_id != app.id:
            return jsonify({'error': 'Rule not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        update_data = {}
        for field in ['event_name', 'field_name', 'data_type', 'is_required', 'expected_pattern', 'condition']:
            if field in data:
                if field == 'event_name':
                    update_data[field] = data[field].lower()
                else:
                    update_data[field] = data[field]
        
        if not update_data:
            return jsonify({'error': 'No fields to update'}), 400
        
        rule = rule_repo.update_rule(rule_id, **update_data)
        
        return jsonify({
            'success': True,
            'rule': rule.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/validation-rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_validation_rule(app_id, rule_id):
    """Delete a validation rule."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        app = app_service.get_app_by_id(app_id)
        if not app:
            return jsonify({'error': 'App not found'}), 404
        
        from app.repositories.validation_rule_repository import ValidationRuleRepository
        rule_repo = ValidationRuleRepository()
        
        # Verify rule belongs to this app
        rule = rule_repo.get_by_id(rule_id)
        if not rule or rule.app_id != app.id:
            return jsonify({'error': 'Rule not found'}), 404
        
        success = rule_repo.delete_by_id(rule_id)
        
        if not success:
            return jsonify({'error': 'Failed to delete rule'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Rule deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/validation-rules/event/<event_name>', methods=['DELETE'])
@login_required
def delete_validation_rules_by_event(app_id, event_name):
    """Delete all validation rules for a specific event."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        app = app_service.get_app_by_id(app_id)
        if not app:
            return jsonify({'error': 'App not found'}), 404
        
        from app.repositories.validation_rule_repository import ValidationRuleRepository
        rule_repo = ValidationRuleRepository()
        
        deleted_count = rule_repo.delete_by_event(app.id, event_name)
        
        return jsonify({
            'success': True,
            'deleted': deleted_count,
            'message': f'Deleted {deleted_count} rule(s) for event: {event_name}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

"""Dashboard controller."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import csv
import io
from app.services.app_service import AppService
from app.services.validation_service import ValidationService
from app.services.log_service import LogService

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
    """Download valid events report as CSV (tab-delimited).
    
    Expects JSON body with:
    - results: List of all validation results
    
    Returns CSV with columns:
    - eventName, eventPayload, dataType, Logs
    
    Only includes events where ALL payloads are valid.
    For invalid events, shows "need to validate further" in Logs column.
    """
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        # Group results by eventName to check if ALL payloads are valid
        from collections import defaultdict
        event_payloads = defaultdict(list)
        for r in results:
            event_payloads[r['eventName']].append(r['validationStatus'])
        
        # Only include events where ALL payloads are valid
        fully_valid_events = [
            event for event, statuses in event_payloads.items()
            if all(status == 'Valid' for status in statuses)
        ]
        
        # Group by eventName to get all events
        event_groups = {}
        for result in results:
            event_name = result['eventName']
            if event_name not in event_groups:
                event_groups[event_name] = []
            event_groups[event_name].append(result)
        
        # Create CSV content (tab-delimited as per beta2.py)
        output = io.StringIO()
        writer = csv.writer(output, delimiter='\t')
        
        # Write header
        writer.writerow(['eventName', 'eventPayload', 'dataType', 'Logs'])
        
        # Write data rows for all events
        all_events = list(event_groups.keys())
        for event_name in all_events:
            event_results = event_groups.get(event_name, [])
            
            # Check if this event is fully valid
            is_fully_valid = event_name in fully_valid_events
            
            # Write first row with event name and first field
            if event_results:
                first_result = event_results[0]
                
                # Determine what to put in the Logs column
                logs_content = "All validations passed" if is_fully_valid else "need to validate further"
                
                writer.writerow([
                    first_result['eventName'],
                    first_result['key'],
                    first_result['expectedType'],
                    logs_content
                ])
                
                # Write remaining rows for this event (without event name and log entry)
                for result in event_results[1:]:
                    writer.writerow([
                        "",  # Empty eventName for subsequent rows
                        result['key'],
                        result['expectedType'],
                        ""  # Empty Logs for subsequent rows
                    ])
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=valid_events_report_{app_id}.csv',
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

"""Dashboard controller."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
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
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    if 'csv_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': 'File must be CSV'}), 400
    
    try:
        # Read CSV content
        csv_content = file.read().decode('utf-8')
        
        # Upload and save rules
        result = validation_service.upload_validation_rules(app_id, csv_content)
        
        if result['success']:
            flash(f"Validation rules uploaded: {result['rules_count']} rules", 'success')
            return jsonify(result), 200
        else:
            flash(f"Error: {result['error']}", 'error')
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/app/<app_id>/stats')
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
    """Get recent logs (AJAX endpoint)."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'error': 'Access denied'}), 403
    
    limit = request.args.get('limit', 100, type=int)
    logs = log_service.get_app_logs(app_id, limit)
    
    return jsonify({
        'logs': [log.to_dict() for log in logs]
    })

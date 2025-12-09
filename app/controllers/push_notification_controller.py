"""Push Notification Controller."""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.app_service import AppService
from app.services.push_notification_service import PushNotificationService
from app.models.firebase_credential import FirebaseCredential
from config.database import db

push_bp = Blueprint('push', __name__)
app_service = AppService()
push_service = PushNotificationService()

@push_bp.route('/app/<app_id>/push-notifications')
@login_required
def index(app_id):
    """Push notification dashboard for an app."""
    if not app_service.user_owns_app(current_user.id, app_id):
        flash('Access denied', 'error')
        return redirect(url_for('dashboard.index'))
    
    app = app_service.get_app_by_id(app_id)
    if not app:
        flash('App not found', 'error')
        return redirect(url_for('dashboard.index'))
        
    # Get recent tokens
    recent_tokens = push_service.get_recent_tokens(app.id)
    
    # Check if credentials exist
    has_credentials = FirebaseCredential.query.filter_by(app_id=app.id).first() is not None
    
    return render_template('push_notifications.html', 
                           app=app, 
                           recent_tokens=recent_tokens,
                           has_credentials=has_credentials)

@push_bp.route('/app/<app_id>/push-notifications/credentials', methods=['POST'])
@login_required
def upload_credentials(app_id):
    """Upload and validate Firebase credentials."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'valid': False, 'message': 'Access denied'}), 403
        
    if 'credentials_file' not in request.files:
        return jsonify({'valid': False, 'message': 'No file uploaded'}), 400
        
    file = request.files['credentials_file']
    if file.filename == '':
        return jsonify({'valid': False, 'message': 'No file selected'}), 400
        
    try:
        content = file.read().decode('utf-8')
        success, msg = push_service.save_credentials(app_id, content)
        return jsonify({'valid': success, 'message': msg})
    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)}), 500

@push_bp.route('/app/<app_id>/push-notifications/credentials', methods=['DELETE'])
@login_required
def delete_credentials(app_id):
    """Delete Firebase credentials."""
    # Check if user owns this app
    app_record = app_service.get_app_by_id(app_id)
    
    if not app_record or app_record.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        credential = FirebaseCredential.query.filter_by(app_id=app_record.id).first()
        
        if not credential:
            return jsonify({'success': False, 'message': 'No credentials found'}), 404
        
        db.session.delete(credential)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Credentials deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@push_bp.route('/app/<app_id>/push-notifications/send', methods=['POST'])
@login_required
def send_notification(app_id):
    """Send push notification."""
    if not app_service.user_owns_app(current_user.id, app_id):
        return jsonify({'success': False, 'status': 'Access denied'}), 403
        
    data = request.get_json()
    success, msg, details = push_service.send_notification(app_id, data)
    
    if success:
        return jsonify({'success': True, **details})
    else:
        return jsonify({'success': False, 'status': msg}), 400

"""Enhanced Authentication Controller with email/OTP registration."""
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import AuthService

auth_bp = Blueprint('auth_email', __name__, url_prefix='/auth')
auth_service = AuthService()


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page - Step 1: Enter email."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        success, message = auth_service.request_registration(email)
        
        if success:
            # Redirect to OTP verification page
            return redirect(url_for('auth_email.verify_otp', email=email))
        else:
            flash(message, 'error')
    
    return render_template('auth/register_email.html')


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Verify OTP and set password - Step 2."""
    email = request.args.get('email') or request.form.get('email')
    
    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('auth_email.register'))
    
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        # Use email as username
        username = email
        
        success, message = auth_service.verify_otp_and_register(
            email, otp, password, password_confirm, username
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('auth_email.login_email'))
        else:
            flash(message, 'error')
            return render_template('auth/verify_otp.html', email=email)
    
    return render_template('auth/verify_otp.html', email=email)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_email():
    """Login with email and password."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        success, message, user_data = auth_service.login(email, password)
        
        if success:
            # Get user object and log them in
            from app.models.user import User
            user = User.query.filter_by(email=email).first()
            login_user(user)
            flash(message, 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash(message, 'error')
    
    return render_template('auth/login_email.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        success, message = auth_service.request_password_reset(email)
        flash(message, 'success' if success else 'error')
        
        if success:
            return redirect(url_for('auth_email.reset_password', email=email))
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password with OTP."""
    email = request.args.get('email') or request.form.get('email')
    
    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('auth_email.forgot_password'))
    
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        new_password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        success, message = auth_service.reset_password(email, otp, new_password, password_confirm)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('auth_email.login_email'))
        else:
            flash(message, 'error')
            return render_template('auth/reset_password.html', email=email)
    
    return render_template('auth/reset_password.html', email=email)


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Logout user."""
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('auth_email.login_email'))


# API Routes for frontend integration

@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint: Request registration OTP."""
    data = request.get_json()
    email = data.get('email', '').strip()
    
    success, message = auth_service.request_registration(email)
    
    return jsonify({
        'success': success,
        'message': message,
        'email': email if success else None
    }), 200 if success else 400


@auth_bp.route('/api/verify-otp', methods=['POST'])
def api_verify_otp():
    """API endpoint: Verify OTP and create account."""
    data = request.get_json()
    email = data.get('email', '').strip()
    otp = data.get('otp', '').strip()
    password = data.get('password', '')
    password_confirm = data.get('password_confirm', '')
    username = data.get('username', '').strip() or None
    
    success, message = auth_service.verify_otp_and_register(
        email, otp, password, password_confirm, username
    )
    
    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 400


@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint: Login and get user info."""
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    success, message, user_data = auth_service.login(email, password)
    
    if success:
        from app.models.user import User
        user = User.query.filter_by(email=email).first()
        login_user(user)
    
    return jsonify({
        'success': success,
        'message': message,
        'user': user_data if success else None
    }), 200 if success else 401


@auth_bp.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    """API endpoint: Request password reset."""
    data = request.get_json()
    email = data.get('email', '').strip()
    
    success, message = auth_service.request_password_reset(email)
    
    return jsonify({
        'success': success,
        'message': message
    }), 200


@auth_bp.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    """API endpoint: Reset password with OTP."""
    data = request.get_json()
    email = data.get('email', '').strip()
    otp = data.get('otp', '').strip()
    new_password = data.get('password', '')
    password_confirm = data.get('password_confirm', '')
    
    success, message = auth_service.reset_password(email, otp, new_password, password_confirm)
    
    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 400

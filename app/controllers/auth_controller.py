"""Authentication controller - Legacy routes redirected to new email-based auth."""
from flask import Blueprint, redirect, url_for
from flask_login import logout_user, login_required, current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Redirect to new email-based login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    # Redirect to new email-based login
    return redirect(url_for('auth_email.login_email'))


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout handler."""
    logout_user()
    return redirect(url_for('auth_email.login_email'))

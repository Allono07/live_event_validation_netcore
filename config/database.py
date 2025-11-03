"""Database initialization module."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize the database."""
    db.init_app(app)
    
    with app.app_context():
        # Import models to ensure they're registered
        from app.models import user, app as app_model, validation_rule, log_entry
        
        # Create tables
        db.create_all()
        
        print("Database initialized successfully!")

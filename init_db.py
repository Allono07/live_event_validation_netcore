from app import create_app
from config.database import db

app = create_app()

with app.app_context():
    # Import models to ensure they are registered
    from app.models import user, app as app_model, validation_rule, log_entry, firebase_credential
    
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully.")

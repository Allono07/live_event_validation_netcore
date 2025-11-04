#!/usr/bin/env python3
"""
Database migration script: Add payload_hash column to log_entries table

This script adds the payload_hash column required for deduplication.
Run this before starting the application if using an existing database.

Usage:
    python3 migrate_add_payload_hash.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

def migrate():
    """Add payload_hash column to log_entries table."""
    
    # Import app configuration
    from config.config import Config
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize database
    db = SQLAlchemy()
    db.init_app(app)
    
    with app.app_context():
        try:
            # Get the database connection
            with db.engine.connect() as connection:
                # Check which database engine we're using
                db_url = str(db.engine.url)
                is_mysql = 'mysql' in db_url
                is_sqlite = 'sqlite' in db_url
                
                print(f"Database: {db_url}")
                print(f"MySQL: {is_mysql}, SQLite: {is_sqlite}")
                
                # Check if column already exists
                if is_mysql:
                    result = connection.execute(text(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_NAME = 'log_entries' AND COLUMN_NAME = 'payload_hash'"
                    ))
                    column_exists = result.fetchone() is not None
                else:  # SQLite
                    result = connection.execute(text(
                        "PRAGMA table_info(log_entries)"
                    ))
                    columns = result.fetchall()
                    column_exists = any(col[1] == 'payload_hash' for col in columns)
                
                if column_exists:
                    print("✓ Column 'payload_hash' already exists!")
                    return True
                
                print("Adding 'payload_hash' column to log_entries table...")
                
                # Add the column
                if is_mysql:
                    connection.execute(text(
                        "ALTER TABLE log_entries ADD COLUMN payload_hash VARCHAR(64) NULL DEFAULT NULL"
                    ))
                    print("✓ Added column to MySQL")
                    
                    # Create index
                    connection.execute(text(
                        "CREATE INDEX idx_log_entries_payload_hash ON log_entries(payload_hash)"
                    ))
                    print("✓ Created index on payload_hash")
                    
                else:  # SQLite
                    connection.execute(text(
                        "ALTER TABLE log_entries ADD COLUMN payload_hash VARCHAR(64) NULL DEFAULT NULL"
                    ))
                    print("✓ Added column to SQLite")
                
                # Commit changes
                connection.commit()
                print("\n✅ Migration completed successfully!")
                return True
                
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print(f"\nIf the column already exists, you can safely ignore this error.")
            print(f"To manually check, run:")
            print(f"  MySQL: DESCRIBE log_entries;")
            print(f"  SQLite: PRAGMA table_info(log_entries);")
            return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)

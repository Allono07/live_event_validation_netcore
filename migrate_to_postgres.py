#!/usr/bin/env python
"""
Migration script: SQLite to PostgreSQL
Transfers all data from SQLite database to PostgreSQL with proper data typing
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import json
import sys
import os

# Configuration
SQLITE_DB = 'instance/validation_dashboard.db'
PG_CONFIG = {
    'dbname': os.getenv('PG_DBNAME', 'live_validation_dashboard'),
    'user': os.getenv('PG_USER', 'postgres'),
    'password': os.getenv('PG_PASSWORD', 'secure_password'),
    'host': os.getenv('PG_HOST', 'localhost'),
    'port': os.getenv('PG_PORT', '5432'),
}

# Table definitions matching SQLAlchemy models
TABLES = {
    'users': {
        'columns': ['id', 'username', 'password', 'email', 'created_at', 'updated_at', 'is_active'],
        'sql': '''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(120) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        '''
    },
    'apps': {
        'columns': ['id', 'app_id', 'name', 'description', 'user_id', 'created_at', 'updated_at', 'is_active'],
        'sql': '''
            CREATE TABLE IF NOT EXISTS apps (
                id SERIAL PRIMARY KEY,
                app_id VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        '''
    },
    'validation_rules': {
        'columns': ['id', 'app_id', 'event_name', 'field_name', 'data_type', 'is_required', 'expected_pattern', 'condition', 'created_at', 'updated_at'],
        'sql': '''
            CREATE TABLE IF NOT EXISTS validation_rules (
                id SERIAL PRIMARY KEY,
                app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
                event_name VARCHAR(200) NOT NULL,
                field_name VARCHAR(200) NOT NULL,
                data_type VARCHAR(50) NOT NULL,
                is_required BOOLEAN DEFAULT FALSE,
                expected_pattern VARCHAR(500),
                condition JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
    },
    'log_entries': {
        'columns': ['id', 'app_id', 'event_name', 'payload', 'is_valid', 'validation_errors', 'created_at'],
        'sql': '''
            CREATE TABLE IF NOT EXISTS log_entries (
                id SERIAL PRIMARY KEY,
                app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
                event_name VARCHAR(200) NOT NULL,
                payload JSONB NOT NULL,
                is_valid BOOLEAN NOT NULL,
                validation_errors JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
    }
}

INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_user_username ON users(username)',
    'CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)',
    'CREATE INDEX IF NOT EXISTS idx_user_active ON users(is_active)',
    'CREATE INDEX IF NOT EXISTS idx_app_user ON apps(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_app_id ON apps(app_id)',
    'CREATE INDEX IF NOT EXISTS idx_app_active ON apps(is_active)',
    'CREATE INDEX IF NOT EXISTS idx_rule_app_event ON validation_rules(app_id, event_name)',
    'CREATE INDEX IF NOT EXISTS idx_rule_event ON validation_rules(event_name)',
    'CREATE INDEX IF NOT EXISTS idx_log_app ON log_entries(app_id)',
    'CREATE INDEX IF NOT EXISTS idx_log_event ON log_entries(event_name)',
    'CREATE INDEX IF NOT EXISTS idx_log_created ON log_entries(created_at DESC)',
    'CREATE INDEX IF NOT EXISTS idx_log_app_created ON log_entries(app_id, created_at DESC)',
]


def connect_sqlite():
    """Connect to SQLite database"""
    if not os.path.exists(SQLITE_DB):
        print(f"❌ SQLite database not found at {SQLITE_DB}")
        return None
    
    try:
        conn = sqlite3.connect(SQLITE_DB)
        conn.row_factory = sqlite3.Row
        print(f"✅ Connected to SQLite: {SQLITE_DB}")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to SQLite: {e}")
        return None


def connect_postgres():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = True
        print(f"✅ Connected to PostgreSQL: {PG_CONFIG['dbname']}")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        print(f"   Config: {PG_CONFIG}")
        return None


def create_tables(pg_conn):
    """Create tables in PostgreSQL"""
    pg_cursor = pg_conn.cursor()
    
    for table_name, table_def in TABLES.items():
        try:
            pg_cursor.execute(table_def['sql'])
            print(f"✅ Created/verified table: {table_name}")
        except Exception as e:
            print(f"⚠️  Error creating table {table_name}: {e}")
    
    pg_conn.commit()


def create_indexes(pg_conn):
    """Create indexes in PostgreSQL"""
    pg_cursor = pg_conn.cursor()
    
    for index_sql in INDEXES:
        try:
            pg_cursor.execute(index_sql)
            print(f"✅ Created index")
        except Exception as e:
            print(f"⚠️  Error creating index: {e}")
    
    pg_conn.commit()


def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migrate data from SQLite table to PostgreSQL"""
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Define boolean columns for type conversion
    boolean_columns = {
        'users': ['is_active'],
        'apps': ['is_active'],
        'validation_rules': ['is_required'],
        'log_entries': ['is_valid']
    }
    
    try:
        # Use only the columns defined in TABLES
        defined_columns = TABLES[table_name]['columns']
        
        # Get data from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"  ℹ️  No data to migrate for {table_name}")
            return 0
        
        # Get column names from SQLite
        sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = sqlite_cursor.fetchall()
        sqlite_columns = {col[1]: col[0] for col in columns_info}  # name: index
        
        # Filter to only use defined columns that exist in SQLite
        columns_to_use = [col for col in defined_columns if col in sqlite_columns]
        
        # Insert into PostgreSQL
        placeholders = ','.join(['%s'] * len(columns_to_use))
        insert_sql = f"INSERT INTO {table_name} ({','.join(columns_to_use)}) VALUES ({placeholders})"
        
        # Get boolean columns for this table
        bool_cols = boolean_columns.get(table_name, [])
        
        migrated = 0
        for row in rows:
            try:
                row_data = []
                for col in columns_to_use:
                    val = row[sqlite_columns[col]]
                    # Convert integer to boolean for boolean columns
                    if col in bool_cols and isinstance(val, int):
                        val = bool(val)
                    row_data.append(val)
                
                pg_cursor.execute(insert_sql, tuple(row_data))
                migrated += 1
            except Exception as e:
                print(f"  ⚠️  Error inserting row into {table_name}: {e}")
                print(f"     Row data: {row_data}")
        
        pg_conn.commit()
        print(f"✅ Migrated {migrated} records to {table_name}")
        return migrated
        
    except Exception as e:
        print(f"❌ Error migrating table {table_name}: {e}")
        return 0


def verify_migration(sqlite_conn, pg_conn):
    """Verify migration by comparing record counts"""
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    print("\n📊 Verification Report:")
    print("-" * 50)
    
    total_sqlite = 0
    total_postgres = 0
    
    for table_name in TABLES.keys():
        try:
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            sqlite_count = sqlite_cursor.fetchone()[0]
            
            pg_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            postgres_count = pg_cursor.fetchone()[0]
            
            match = "✅" if sqlite_count == postgres_count else "❌"
            print(f"{match} {table_name:20} SQLite: {sqlite_count:6} → PostgreSQL: {postgres_count:6}")
            
            total_sqlite += sqlite_count
            total_postgres += postgres_count
            
        except Exception as e:
            print(f"❌ Error checking {table_name}: {e}")
    
    print("-" * 50)
    print(f"{'✅' if total_sqlite == total_postgres else '❌'} Total: {total_sqlite:6} → {total_postgres:6}")
    
    return total_sqlite == total_postgres


def main():
    """Main migration function"""
    print("\n" + "=" * 60)
    print("  SQLite → PostgreSQL Migration")
    print("=" * 60 + "\n")
    
    # Connect to databases
    sqlite_conn = connect_sqlite()
    if not sqlite_conn:
        return False
    
    pg_conn = connect_postgres()
    if not pg_conn:
        sqlite_conn.close()
        return False
    
    try:
        # Create tables
        print("\n📋 Creating PostgreSQL tables...")
        create_tables(pg_conn)
        
        # Migrate data
        print("\n📤 Migrating data...")
        total_migrated = 0
        for table_name in TABLES.keys():
            migrated = migrate_table(sqlite_conn, pg_conn, table_name)
            total_migrated += migrated
        
        # Create indexes
        print("\n🔍 Creating indexes...")
        create_indexes(pg_conn)
        
        # Verify migration
        print("\n")
        success = verify_migration(sqlite_conn, pg_conn)
        
        if success:
            print("\n" + "=" * 60)
            print("  ✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"\n📌 Next steps:")
            print(f"   1. Update Flask config: DATABASE_URL=postgresql://...")
            print(f"   2. Test the application: python run.py")
            print(f"   3. Backup your SQLite database for safety")
            print(f"   4. Run load tests to verify performance")
        else:
            print("\n" + "=" * 60)
            print("  ⚠️  MIGRATION COMPLETED WITH WARNINGS")
            print("=" * 60)
            print(f"\n   Some record counts don't match!")
            print(f"   Please verify the data manually.")
        
        return success
        
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

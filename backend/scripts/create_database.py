#!/usr/bin/env python3
"""
Create PostgreSQL database if it doesn't exist.
Used by E2E test server startup scripts.
"""

import os
import sys

def create_database_if_not_exists():
    """Create database if it doesn't exist."""
    # Use same auto-detection logic as backend
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Try to auto-resolve if DATABASE_URL not set
        try:
            import sys
            from pathlib import Path
            # Add backend directory to path if needed
            script_dir = Path(__file__).parent.parent
            if str(script_dir) not in sys.path:
                sys.path.insert(0, str(script_dir))
            from app.utils.db_host import resolve_db_host
            database_url = resolve_db_host()
        except Exception as e:
            print(f"Note: Could not auto-resolve DATABASE_URL: {e}")
            print("Skipping database creation - DATABASE_URL must be set")
            return True
    
    if not database_url or not database_url.startswith("postgresql"):
        print("Not a PostgreSQL connection string, skipping database creation")
        return True
    
    try:
        from urllib.parse import urlparse
        import psycopg2
        
        parsed = urlparse(database_url)
        db_name = parsed.path[1:] if parsed.path.startswith('/') else parsed.path
        
        # Connect to default 'postgres' database to create target database
        admin_conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database='postgres'
        )
        admin_conn.autocommit = True
        cursor = admin_conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✓ Created database: {db_name}")
        else:
            print(f"✓ Database {db_name} already exists")
        
        cursor.close()
        admin_conn.close()
        return True
        
    except ImportError:
        print("Note: psycopg2 not available, skipping database creation check")
        return True
    except Exception as e:
        print(f"Warning: Could not create database: {e}")
        return False

if __name__ == "__main__":
    success = create_database_if_not_exists()
    sys.exit(0 if success else 1)


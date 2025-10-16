#!/usr/bin/env python3
"""
Database migration script to add deptname field to users table
Usage: python migrate_deptname.py
"""

import sys
import os
from sqlalchemy import text

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal

def run_migration():
    """Run the migration to add deptname column to users table"""
    try:
        print("🚀 Starting migration: Add deptname to users table")
        
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()
            
            try:
                # Check if column already exists
                result = connection.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'deptname'
                """))
                
                if result.fetchone():
                    print("✅ Column 'deptname' already exists in users table")
                    trans.rollback()
                    return True
                
                # Add deptname column
                print("📝 Adding deptname column to users table...")
                connection.execute(text("""
                    ALTER TABLE users ADD COLUMN deptname VARCHAR(100)
                """))
                
                # Add comment (PostgreSQL specific - adjust for other databases)
                try:
                    connection.execute(text("""
                        COMMENT ON COLUMN users.deptname IS 'Department name of the user'
                    """))
                    print("📝 Added comment to deptname column")
                except Exception as e:
                    print(f"⚠️  Could not add comment (may not be supported): {e}")
                
                # Create index for better performance
                print("📝 Creating index on deptname column...")
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_deptname ON users(deptname)
                """))
                
                # Commit the transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                
                # Verify the migration
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'deptname'
                """))
                
                column_info = result.fetchone()
                if column_info:
                    print(f"✅ Verification: deptname column created")
                    print(f"   - Type: {column_info[1]}")
                    print(f"   - Nullable: {column_info[2]}")
                else:
                    print("❌ Verification failed: deptname column not found")
                    return False
                
                return True
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def rollback_migration():
    """Rollback the migration (remove deptname column)"""
    try:
        print("🔄 Rolling back migration: Remove deptname from users table")
        
        with engine.connect() as connection:
            trans = connection.begin()
            
            try:
                # Check if column exists
                result = connection.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'deptname'
                """))
                
                if not result.fetchone():
                    print("✅ Column 'deptname' does not exist in users table")
                    trans.rollback()
                    return True
                
                # Drop index first
                print("📝 Dropping index on deptname column...")
                connection.execute(text("""
                    DROP INDEX IF EXISTS idx_users_deptname
                """))
                
                # Drop column
                print("📝 Removing deptname column from users table...")
                connection.execute(text("""
                    ALTER TABLE users DROP COLUMN deptname
                """))
                
                trans.commit()
                print("✅ Rollback completed successfully!")
                return True
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate deptname field to users table')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        if args.rollback:
            print("Would rollback: Remove deptname column from users table")
        else:
            print("Would apply: Add deptname column to users table")
        sys.exit(0)
    
    if args.rollback:
        success = rollback_migration()
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)

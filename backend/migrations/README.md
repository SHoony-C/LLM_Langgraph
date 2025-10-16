# Database Migrations

This directory contains database migration scripts for the LLM UI application.

## Available Migrations

### add_deptname_to_users.sql
Adds a `deptname` (department name) field to the users table.

**Changes:**
- Adds `deptname VARCHAR(100)` column to `users` table
- Creates index `idx_users_deptname` for better query performance
- Column is nullable to support existing users

## Running Migrations

### Option 1: Using Python Script (Recommended)
```bash
cd backend
python migrate_deptname.py
```

**Additional options:**
```bash
# Dry run (see what would be done)
python migrate_deptname.py --dry-run

# Rollback migration
python migrate_deptname.py --rollback

# Rollback dry run
python migrate_deptname.py --rollback --dry-run
```

### Option 2: Manual SQL Execution
```bash
# Connect to your database and run:
psql -d your_database -f migrations/add_deptname_to_users.sql
```

## Migration Details

### Before Migration
Users table structure:
- id (Primary Key)
- username
- mail
- hashed_password
- created_at
- loginid

### After Migration
Users table structure:
- id (Primary Key)
- username
- mail
- hashed_password
- created_at
- loginid
- **deptname** (New field)

## Rollback

If you need to rollback the migration:
```bash
python migrate_deptname.py --rollback
```

This will:
1. Drop the `idx_users_deptname` index
2. Remove the `deptname` column from the `users` table

## Notes

- The `deptname` field is optional (nullable)
- Existing users will have `NULL` values for `deptname` until they update their profile
- The migration is safe to run multiple times (idempotent)
- Always backup your database before running migrations in production

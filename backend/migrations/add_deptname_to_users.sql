-- Add deptname column to users table
-- Migration: Add deptname field to users table
-- Date: 2024-10-16

-- Add deptname column to users table
ALTER TABLE users ADD COLUMN deptname VARCHAR(100);

-- Add comment to the column
COMMENT ON COLUMN users.deptname IS 'Department name of the user';

-- Create index on deptname for better query performance (optional)
CREATE INDEX idx_users_deptname ON users(deptname);

-- Update existing users with default deptname if needed (optional)
-- UPDATE users SET deptname = 'General' WHERE deptname IS NULL;

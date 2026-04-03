-- 1. Drop the existing constraint that limits roles to 'admin', 'lawyer', or 'staff'
ALTER TABLE admins DROP CONSTRAINT IF EXISTS admins_role_check;

-- 2. Add the primary_role column to support landing page redirection
ALTER TABLE admins ADD COLUMN IF NOT EXISTS primary_role TEXT DEFAULT 'staff';

-- 3. Update existing admins to have a primary_role based on their current role
UPDATE admins SET primary_role = role WHERE primary_role = 'staff';

-- 4. Verify that 'role' can now hold multiple comma-separated values (automatic after dropping check)
COMMENT ON COLUMN admins.role IS 'Holds comma-separated role strings (e.g. admin,marketing)';
COMMENT ON COLUMN admins.primary_role IS 'The primary landing dashboard (e.g. marketing or staff)';

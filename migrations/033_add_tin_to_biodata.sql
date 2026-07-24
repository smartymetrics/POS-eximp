
-- Add TIN support to Bio Data and Staff Profiles
ALTER TABLE biodata_submissions ADD COLUMN IF NOT EXISTS tin TEXT;
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS tin TEXT;

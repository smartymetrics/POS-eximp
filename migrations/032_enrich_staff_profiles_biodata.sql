-- Update staff_profiles to support bio data fields
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS passport_photo_path TEXT;
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS signature_path TEXT;
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS passport_photo_url TEXT;
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS signature_url TEXT;

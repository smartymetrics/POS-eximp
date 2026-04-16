-- HR Phase 6: Geofencing & Security Flags
-- This migration adds security tracking to attendance records.

ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS latitude NUMERIC;
ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS longitude NUMERIC;
ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS distance_meters NUMERIC;
ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS is_suspicious BOOLEAN DEFAULT FALSE;
ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS suspicious_reason TEXT;
ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS device_type VARCHAR(100);
ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS ip_address VARCHAR(100);
ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS user_agent TEXT;

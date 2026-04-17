-- HR Phase 8: Remote Work Support
ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS is_remote BOOLEAN DEFAULT FALSE;

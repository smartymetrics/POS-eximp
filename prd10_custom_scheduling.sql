-- Migration: Add custom scheduling columns to report_schedules
-- These allow for specific day/time configuration (e.g. Friday 5:00 PM)

ALTER TABLE report_schedules 
ADD COLUMN IF NOT EXISTS day_of_week INTEGER DEFAULT 1; -- 1 (Mon) to 7 (Sun)

ALTER TABLE report_schedules 
ADD COLUMN IF NOT EXISTS day_of_month INTEGER DEFAULT 1; -- 1 to 31

ALTER TABLE report_schedules 
ADD COLUMN IF NOT EXISTS hour INTEGER DEFAULT 8; -- 0 to 23

ALTER TABLE report_schedules 
ADD COLUMN IF NOT EXISTS minute INTEGER DEFAULT 0; -- 0 to 59

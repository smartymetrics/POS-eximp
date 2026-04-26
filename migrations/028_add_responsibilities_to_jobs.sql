-- Add responsibilities column to job_requisitions
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS responsibilities TEXT;

-- Migration to add missing fields to job_requisitions
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS justification TEXT;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS headcount INTEGER DEFAULT 1;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS responsibilities TEXT; -- Just in case previous migration was missed

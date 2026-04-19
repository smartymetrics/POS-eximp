-- Migration: Add Staff Visibility Control for Legal Matters
-- Date: April 2026
-- Purpose: Prevent staff from viewing confidential matters unless explicitly marked visible by HR/Legal

ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS staff_visible BOOLEAN DEFAULT FALSE;

-- Add index for faster filtering
CREATE INDEX IF NOT EXISTS idx_legal_matters_staff_visible ON legal_matters(staff_visible, staff_id);

-- Audit comment
COMMENT ON COLUMN legal_matters.staff_visible IS 'When TRUE, the associated staff member can view this matter. Default FALSE (confidential). Only HR/Legal can toggle.';

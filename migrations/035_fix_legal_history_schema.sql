-- Migration: Add performed_by_name to legal_matter_history
-- Date: May 2026
-- Purpose: Fix missing column causing 500 errors in the legal audit trail during document operations.

ALTER TABLE legal_matter_history ADD COLUMN IF NOT EXISTS performed_by_name TEXT;

-- Update existing records if possible (optional but good practice)
-- Since we can't join public.admins easily across schemas in some setups without specific permissions, 
-- we'll just ensure the column is there for future inserts.

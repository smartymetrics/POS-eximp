-- Migration: Add budget and vendor tracking to procurement
-- Description: Adds budget column and ensures vendor tracking is robust

ALTER TABLE procurement_expenses 
ADD COLUMN IF NOT EXISTS budget DECIMAL(15, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS vendor_name TEXT,
ADD COLUMN IF NOT EXISTS expense_date DATE DEFAULT CURRENT_DATE;

ALTER TABLE estate_drafts
ADD COLUMN IF NOT EXISTS total_budget DECIMAL(15, 2) DEFAULT 0;

ALTER TABLE properties
ADD COLUMN IF NOT EXISTS budget DECIMAL(15, 2) DEFAULT 0;

-- Refresh PostgREST schema cache
NOTIFY pgrst, 'reload schema';

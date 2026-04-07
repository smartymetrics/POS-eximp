-- ============================================================
-- MIGRATION: Void Expenditure Support
-- ============================================================

-- 1. Update the status check constraint to include 'voided'
ALTER TABLE expenditure_requests DROP CONSTRAINT IF EXISTS expenditure_requests_status_check;
ALTER TABLE expenditure_requests ADD CONSTRAINT expenditure_requests_status_check 
    CHECK (status IN ('pending', 'awaiting_vendor_data', 'approved', 'paid', 'rejected', 'voided'));

-- 2. Add audit fields for voiding
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS void_reason TEXT;
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ;
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS voided_by UUID REFERENCES admins(id);

-- Optional: Index on status for faster filtering
CREATE INDEX IF NOT EXISTS idx_expenditure_status ON expenditure_requests (status);

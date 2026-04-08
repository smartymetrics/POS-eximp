-- Ensure WHT remittance columns exist in expenditure_requests
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS is_wht_remitted BOOLEAN DEFAULT false;
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS wht_remittance_ref VARCHAR(255);
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS wht_remitted_at TIMESTAMPTZ;
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS wht_remitted_by UUID REFERENCES admins(id);

-- Update status constraint to include all relevant states
ALTER TABLE expenditure_requests DROP CONSTRAINT IF EXISTS expenditure_requests_status_check;
ALTER TABLE expenditure_requests ADD CONSTRAINT expenditure_requests_status_check 
    CHECK (status IN ('pending_verification', 'pending', 'awaiting_vendor_data', 'approved', 'partially_paid', 'paid', 'rejected', 'voided'));

-- Refresh PostgREST schema cache
NOTIFY pgrst, 'reload schema';

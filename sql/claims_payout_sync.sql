
-- Update expenditure_requests to support CRM fraud shield and Invoice Sync
ALTER TABLE expenditure_requests 
ADD COLUMN IF NOT EXISTS invoice_id UUID REFERENCES invoices(id),
ADD COLUMN IF NOT EXISTS is_high_risk BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS risk_notes TEXT,
ADD COLUMN IF NOT EXISTS source_platform VARCHAR(50) DEFAULT 'manual', -- 'manual', 'vendor_portal', 'rep_portal'
ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) DEFAULT 'unverified'; -- 'unverified', 'verified', 'rejected'

-- Update pending_verifications for completeness
ALTER TABLE pending_verifications
ADD COLUMN IF NOT EXISTS source_platform VARCHAR(50) DEFAULT 'client_form'; 


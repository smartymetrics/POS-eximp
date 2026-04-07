-- ============================================================
-- EXIMP & CLOVES INFRASTRUCTURE LIMITED
-- Accounts Payable & Partial Payouts (PRD v12)
-- ============================================================

-- 1. Upgrade the Vendor Bills / Requests Table
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS vendor_invoice_number VARCHAR(100);
ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS amount_paid DECIMAL(15,2) DEFAULT 0;

-- Backfill legacy "paid" rows so accounting balances perfectly
UPDATE expenditure_requests 
SET amount_paid = net_payout_amount 
WHERE status = 'paid' AND amount_paid = 0;

-- Allow 'partially_paid' and 'voided' in string constraint
ALTER TABLE expenditure_requests DROP CONSTRAINT IF EXISTS expenditure_requests_status_check;
ALTER TABLE expenditure_requests ADD CONSTRAINT expenditure_requests_status_check 
    CHECK (status IN ('pending_verification', 'pending', 'awaiting_vendor_data', 'approved', 'partially_paid', 'paid', 'rejected', 'voided'));

-- 2. Create the Ledger tracking discrete payouts against a bill
CREATE TABLE IF NOT EXISTS expenditure_payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    request_id UUID REFERENCES expenditure_requests(id) ON DELETE CASCADE,
    amount DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(50),
    reference VARCHAR(255),
    paid_by UUID REFERENCES admins(id),
    paid_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE expenditure_payments ENABLE ROW LEVEL SECURITY;
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'expenditure_payments' AND policyname = 'Admins have full access to expenditure_payments'
    ) THEN
        CREATE POLICY "Admins have full access to expenditure_payments" ON expenditure_payments FOR ALL TO authenticated USING (true);
    END IF;
END $$;

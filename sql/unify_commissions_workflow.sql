
-- ============================================================
-- EXIMP & CLOVES INFRASTRUCTURE LIMITED
-- Unified Payout & Commission Workflow (Migration)
-- ============================================================

-- 1. Update expenditure_requests to store structural IDs
ALTER TABLE expenditure_requests 
ADD COLUMN IF NOT EXISTS payment_id UUID REFERENCES payments(id),
ADD COLUMN IF NOT EXISTS pending_verification_id UUID REFERENCES pending_verifications(id);

-- 2. Update commission_earnings to support Partners and prevent duplicates
ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS vendor_id UUID REFERENCES vendors(id),
ALTER COLUMN sales_rep_id DROP NOT NULL;

-- 3. Add unique constraints to prevent double-counting commissions
-- We want to ensure that for a single payment, a Sales Rep or Vendor only earns commission ONCE.
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_commission_rep_payment') THEN
        ALTER TABLE commission_earnings ADD CONSTRAINT unique_commission_rep_payment UNIQUE (payment_id, sales_rep_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_commission_vendor_payment') THEN
        ALTER TABLE commission_earnings ADD CONSTRAINT unique_commission_vendor_payment UNIQUE (payment_id, vendor_id);
    END IF;
END $$;

-- 4. Index for performance on the new vendor_id column
CREATE INDEX IF NOT EXISTS idx_commission_earnings_vendor ON commission_earnings(vendor_id);

-- Commission & WHT Professionalization Migration
-- Objective: Integrate transparent WHT calculations and multi-tier commission rates.

-- 1. Update Sales Reps to support flexible commission and WHT rates
ALTER TABLE sales_reps 
ADD COLUMN IF NOT EXISTS gross_commission_rate DECIMAL DEFAULT 10.0,
ADD COLUMN IF NOT EXISTS wht_rate DECIMAL DEFAULT 5.0;

-- 2. Update Vendors to support dual-purpose Commission Partner status
ALTER TABLE vendors
ADD COLUMN IF NOT EXISTS is_commission_partner BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS gross_commission_rate DECIMAL DEFAULT 15.0,
ADD COLUMN IF NOT EXISTS wht_rate DECIMAL DEFAULT 5.0;

-- 3. Upgrade Commission Earnings to track full financial breakdown
ALTER TABLE commission_earnings
ADD COLUMN IF NOT EXISTS gross_commission DECIMAL DEFAULT 0,
ADD COLUMN IF NOT EXISTS wht_amount DECIMAL DEFAULT 0,
ADD COLUMN IF NOT EXISTS net_commission DECIMAL DEFAULT 0;

-- 4. Backfill existing earnings (Net = Current Amount, Gross = Net / 0.95 approx, WHT = Gross * 0.05)
-- Assuming a 5% WHT for backfill purposes to maintain accounting integrity.
UPDATE commission_earnings
SET 
    gross_commission = commission_amount,
    wht_amount = commission_amount * 0.05,
    net_commission = commission_amount * 0.95
WHERE gross_commission = 0;

-- 5. Add Tax Remittance tracking to commissions
ALTER TABLE commission_earnings
ADD COLUMN IF NOT EXISTS is_wht_remitted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS wht_remitted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS wht_receipt_ref TEXT;

-- 6. Add Audit metadata to vendors
ALTER TABLE vendors
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

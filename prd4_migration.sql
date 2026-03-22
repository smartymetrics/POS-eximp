-- ============================================================
-- COMMISSION MANAGEMENT (PRD 4)
-- Run this block in the Supabase SQL Editor
-- ============================================================

-- 1. SYSTEM SETTINGS (for default global rate)
CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_by UUID REFERENCES admins(id),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO system_settings (key, value) VALUES ('default_commission_rate', '5.00')
ON CONFLICT (key) DO NOTHING;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- 2. COMMISSION RATES
CREATE TABLE IF NOT EXISTS commission_rates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sales_rep_id UUID NOT NULL REFERENCES sales_reps(id),
    estate_name VARCHAR(255) NOT NULL,
    rate DECIMAL(5,2) NOT NULL,
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    reason VARCHAR(255),
    set_by UUID NOT NULL REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_commission_rates_active 
    ON commission_rates(sales_rep_id, estate_name) 
    WHERE effective_to IS NULL;

ALTER TABLE commission_rates ENABLE ROW LEVEL SECURITY;

-- 3. PAYOUT BATCHES
CREATE TABLE IF NOT EXISTS payout_batches (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sales_rep_id UUID NOT NULL REFERENCES sales_reps(id),
    total_amount DECIMAL(15,2) NOT NULL,
    reference VARCHAR(255),
    notes TEXT,
    paid_by UUID NOT NULL REFERENCES admins(id),
    paid_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE payout_batches ENABLE ROW LEVEL SECURITY;

-- 4. COMMISSION EARNINGS
CREATE TABLE IF NOT EXISTS commission_earnings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sales_rep_id UUID NOT NULL REFERENCES sales_reps(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    payment_id UUID NOT NULL REFERENCES payments(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    estate_name VARCHAR(255) NOT NULL,
    payment_amount DECIMAL(15,2) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,
    commission_amount DECIMAL(15,2) NOT NULL,
    
    adjusted_amount DECIMAL(15,2),
    adjustment_reason TEXT,
    adjusted_by UUID REFERENCES admins(id),
    adjusted_at TIMESTAMPTZ,
    
    final_amount DECIMAL(15,2) GENERATED ALWAYS AS (
        COALESCE(adjusted_amount, commission_amount)
    ) STORED,
    
    is_paid BOOLEAN DEFAULT false,
    paid_at TIMESTAMPTZ,
    paid_by UUID REFERENCES admins(id),
    payout_reference VARCHAR(255),
    payout_batch_id UUID REFERENCES payout_batches(id),
    
    rep_notified BOOLEAN DEFAULT false,
    rep_notified_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_commission_earnings_rep ON commission_earnings(sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_commission_earnings_invoice ON commission_earnings(invoice_id);
CREATE INDEX IF NOT EXISTS idx_commission_earnings_unpaid ON commission_earnings(sales_rep_id, is_paid) WHERE is_paid = false;

ALTER TABLE commission_earnings ENABLE ROW LEVEL SECURITY;

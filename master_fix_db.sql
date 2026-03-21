-- ============================================================
-- MASTER FIX: ENSURE ALL PRD V2 COLUMNS EXIST
-- Run this in your Supabase SQL Editor
-- ============================================================

-- 1. FIX CLIENTS TABLE
DO $$ BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='referral_source') THEN
        ALTER TABLE clients ADD COLUMN referral_source VARCHAR(100);
    END IF;
    -- Add other potential missing KYC fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='source_of_income') THEN
        ALTER TABLE clients ADD COLUMN source_of_income VARCHAR(100);
    END IF;
END $$;

-- 2. FIX INVOICES TABLE
DO $$ BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='sales_rep_name') THEN
        ALTER TABLE invoices ADD COLUMN sales_rep_name VARCHAR(255);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='property_name') THEN
        ALTER TABLE invoices ADD COLUMN property_name VARCHAR(255);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='property_location') THEN
        ALTER TABLE invoices ADD COLUMN property_location VARCHAR(255);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='plot_size_sqm') THEN
        ALTER TABLE invoices ADD COLUMN plot_size_sqm DECIMAL(10,2);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='source') THEN
        ALTER TABLE invoices ADD COLUMN source VARCHAR(50) DEFAULT 'manual';
    END IF;
END $$;

-- 3. FIX PAYMENTS TABLE
DO $$ BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='payments' AND column_name='is_voided') THEN
        ALTER TABLE payments ADD COLUMN is_voided BOOLEAN DEFAULT false;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='payments' AND column_name='voided_by') THEN
        ALTER TABLE payments ADD COLUMN voided_by UUID REFERENCES admins(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='payments' AND column_name='voided_at') THEN
        ALTER TABLE payments ADD COLUMN voided_at TIMESTAMPTZ;
    END IF;
END $$;

-- 4. ENSURE TABLES FOR PRD V2 EXIST
CREATE TABLE IF NOT EXISTS activity_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    client_id UUID REFERENCES clients(id),
    invoice_id UUID REFERENCES invoices(id),
    performed_by UUID REFERENCES admins(id),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales_reps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    commission_rate DECIMAL(5,2) DEFAULT 5.0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS unmatched_reps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name_from_form VARCHAR(255) UNIQUE NOT NULL,
    times_seen INTEGER DEFAULT 1,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    is_resolved BOOLEAN DEFAULT false,
    resolved_to UUID REFERENCES sales_reps(id)
);

CREATE TABLE IF NOT EXISTS pending_verifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    payment_proof_url TEXT,
    deposit_amount DECIMAL(15,2),
    payment_date VARCHAR(100),
    sales_rep_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'rejected')),
    reviewed_by UUID REFERENCES admins(id),
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. REFRESH SCHEMA CACHE
NOTIFY pgrst, 'reload schema';

-- 6. ENSURE INDEXES FOR ANALYTICS PEFORMANCE
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date);

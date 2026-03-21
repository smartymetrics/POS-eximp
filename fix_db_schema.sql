-- ============================================================
-- FIX DATABASE SCHEMA (PRD 1 & 2 MISSING PIECES)
-- Run this in your Supabase SQL Editor
-- ============================================================

-- 1. Ensure sales_rep_name exists in invoices
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='sales_rep_name') THEN
        ALTER TABLE invoices ADD COLUMN sales_rep_name VARCHAR(255);
    END IF;
END $$;

-- 2. Ensure activity_log exists
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

-- 3. Ensure sales_reps and unmatched_reps exist
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

-- 4. Ensure pending_verifications and void_log exist
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

CREATE TABLE IF NOT EXISTS void_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    voided_by UUID NOT NULL REFERENCES admins(id),
    reason TEXT NOT NULL,
    amount_reversed DECIMAL(15,2),
    notify_client BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Ensure report_schedules exists
CREATE TABLE IF NOT EXISTS report_schedules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    report_type VARCHAR(100) NOT NULL,
    frequency VARCHAR(50) NOT NULL,
    recipients TEXT[] NOT NULL,
    format VARCHAR(20) DEFAULT 'pdf',
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Important: Refresh Schema Cache
-- Some errors persist because Postgrest (Supabase API) cache is stale.
NOTIFY pgrst, 'reload schema';

-- 7. RLS (Optional but recommended if tables were missing)
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_reps ENABLE ROW LEVEL SECURITY;
ALTER TABLE unmatched_reps ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE void_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_schedules ENABLE ROW LEVEL SECURITY;

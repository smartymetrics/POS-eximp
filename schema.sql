-- ============================================================
-- EXIMP & CLOVES INFRASTRUCTURE LIMITED
-- Finance System - Database Schema
-- Run this in your Supabase SQL Editor
-- ============================================================

-- ADMINS TABLE
CREATE TABLE IF NOT EXISTS admins (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'staff' CHECK (role IN ('admin', 'staff')),
    is_active BOOLEAN DEFAULT true,
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- CLIENTS TABLE
CREATE TABLE IF NOT EXISTS clients (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    added_by UUID REFERENCES admins(id),
    
    -- KYC fields for PRD v2
    title VARCHAR(20),
    middle_name VARCHAR(100),
    gender VARCHAR(20),
    dob VARCHAR(50),
    marital_status VARCHAR(50),
    occupation VARCHAR(100),
    nin VARCHAR(50),
    id_number VARCHAR(100),
    id_document_url TEXT,
    nationality VARCHAR(100),
    passport_photo_url TEXT,
    nok_name VARCHAR(255),
    nok_phone VARCHAR(50),
    nok_email VARCHAR(255),
    nok_occupation VARCHAR(100),
    nok_relationship VARCHAR(100),
    nok_address TEXT,
    source_of_income VARCHAR(100),
    referral_source VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- PROPERTIES TABLE
CREATE TABLE IF NOT EXISTS properties (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    estate_name VARCHAR(255),
    plot_size_sqm DECIMAL(10,2),
    price_per_sqm DECIMAL(15,2),
    starting_price DECIMAL(15,2) NOT NULL,
    description TEXT,
    available_plot_sizes TEXT,
    is_active BOOLEAN DEFAULT true,
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- INVOICE NUMBER SEQUENCE TABLE
CREATE TABLE IF NOT EXISTS invoice_sequences (
    id SERIAL PRIMARY KEY,
    prefix VARCHAR(10) DEFAULT 'EC',
    last_number INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert the initial sequence row
INSERT INTO invoice_sequences (prefix, last_number) VALUES ('EC', 0)
ON CONFLICT DO NOTHING;

-- INVOICES TABLE
CREATE TABLE IF NOT EXISTS invoices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,  -- e.g. EC-000001
    client_id UUID NOT NULL REFERENCES clients(id),
    property_id UUID REFERENCES properties(id),
    
    -- Property snapshot (in case property is later edited)
    property_name VARCHAR(255),
    property_location VARCHAR(255),
    plot_size_sqm DECIMAL(10,2),
    
    amount DECIMAL(15,2) NOT NULL,
    amount_paid DECIMAL(15,2) DEFAULT 0,
    balance_due DECIMAL(15,2) GENERATED ALWAYS AS (amount - amount_paid) STORED,
    
    payment_terms VARCHAR(100) DEFAULT 'Outright',  -- Outright / Installment
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    
    status VARCHAR(50) DEFAULT 'unpaid' CHECK (status IN ('unpaid', 'partial', 'paid', 'voided', 'overdue')),
    notes TEXT,
    
    -- New fields for PRD v2
    sales_rep_name VARCHAR(255),
    co_owner_name VARCHAR(255),
    co_owner_email VARCHAR(255),
    signature_url TEXT,
    payment_proof_url TEXT,
    passport_photo_url TEXT,
    source VARCHAR(50) DEFAULT 'manual', -- manual / google_form

    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- PAYMENTS TABLE
CREATE TABLE IF NOT EXISTS payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    reference VARCHAR(100) NOT NULL,  -- e.g. transaction ref / bank teller
    amount DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(100),  -- Bank Transfer / Cash / Online
    payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT,
    
    -- Voiding fields for PRD v2
    is_voided BOOLEAN DEFAULT false,
    voided_by UUID REFERENCES admins(id),
    voided_at TIMESTAMPTZ,

    recorded_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- EMAIL LOGS TABLE (track every email sent)
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID REFERENCES clients(id),
    invoice_id UUID REFERENCES invoices(id),
    email_type VARCHAR(100) NOT NULL,  -- invoice / receipt / statement
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    status VARCHAR(50) DEFAULT 'sent' CHECK (status IN ('sent', 'failed')),
    resend_message_id VARCHAR(255),
    sent_by UUID REFERENCES admins(id),
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================

-- Auto-generate invoice number (EC-000001, EC-000002, ...)
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS VARCHAR AS $$
DECLARE
    new_number INTEGER;
    prefix VARCHAR(10);
    formatted VARCHAR(50);
BEGIN
    UPDATE invoice_sequences
    SET last_number = last_number + 1, updated_at = NOW()
    WHERE id = 1
    RETURNING last_number, invoice_sequences.prefix INTO new_number, prefix;
    
    formatted := prefix || '-' || LPAD(new_number::TEXT, 6, '0');
    RETURN formatted;
END;
$$ LANGUAGE plpgsql;

-- Auto-update invoice status when payments are added
CREATE OR REPLACE FUNCTION update_invoice_status()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE invoices
    SET 
        amount_paid = (
            SELECT COALESCE(SUM(amount), 0)
            FROM payments
            WHERE invoice_id = NEW.invoice_id AND is_voided = false
        ),
        status = CASE
            WHEN (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id = NEW.invoice_id AND is_voided = false) >= amount THEN 'paid'
            WHEN (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id = NEW.invoice_id AND is_voided = false) > 0 THEN 'partial'
            ELSE 'unpaid'
        END,
        updated_at = NOW()
    WHERE id = NEW.invoice_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS after_payment_insert ON payments;
CREATE TRIGGER after_payment_insert
AFTER INSERT ON payments
FOR EACH ROW EXECUTE FUNCTION update_invoice_status();

-- Trigger for updates (voiding payments)
DROP TRIGGER IF EXISTS after_payment_update ON payments;
CREATE TRIGGER after_payment_update
AFTER UPDATE ON payments
FOR EACH ROW EXECUTE FUNCTION update_invoice_status();

-- ============================================================
-- ROW LEVEL SECURITY (RLS) - Enable in Supabase
-- ============================================================
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- ANALYTICS & ACTIVITY LOGGING (PRD 1)
-- ============================================================

-- ACTIVITY LOG TABLE
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_sales_rep ON invoices(sales_rep_name);
CREATE INDEX IF NOT EXISTS idx_invoices_property_name ON invoices(property_name);
CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_clients_created_at ON clients(created_at);

ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- NEW TABLES FOR PRD V2
-- ============================================================

-- PENDING VERIFICATIONS TABLE
CREATE TABLE IF NOT EXISTS pending_verifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    payment_proof_url TEXT,
    deposit_amount DECIMAL(15,2),
    payment_date VARCHAR(100),
    sales_rep_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending'
        CHECK (status IN ('pending', 'confirmed', 'rejected')),
    reviewed_by UUID REFERENCES admins(id),
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- VOID LOG TABLE
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

-- RLS for new tables
ALTER TABLE pending_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE void_log ENABLE ROW LEVEL SECURITY;

-- DUE DATE CHANGES TABLE
CREATE TABLE IF NOT EXISTS due_date_changes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    old_date DATE,
    new_date DATE NOT NULL,
    reason TEXT NOT NULL,
    changed_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE due_date_changes ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- SALES REPRESENTATIVES (PRD 2)
-- ============================================================

-- SALES REPS TABLE
CREATE TABLE IF NOT EXISTS sales_reps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    commission_rate DECIMAL(5,2) DEFAULT 5.0, -- Default 5%
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- UNMATCHED REPS TABLE (To capture misspelled or new names from forms)
CREATE TABLE IF NOT EXISTS unmatched_reps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name_from_form VARCHAR(255) UNIQUE NOT NULL,
    times_seen INTEGER DEFAULT 1,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    is_resolved BOOLEAN DEFAULT false,
    resolved_to UUID REFERENCES sales_reps(id)
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_sales_reps_name ON sales_reps(name);
CREATE INDEX IF NOT EXISTS idx_unmatched_reps_unresolved ON unmatched_reps(is_resolved) WHERE is_resolved = false;

ALTER TABLE sales_reps ENABLE ROW LEVEL SECURITY;
ALTER TABLE unmatched_reps ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- REPORT SCHEDULES (PRD 2)
-- ============================================================

CREATE TABLE IF NOT EXISTS report_schedules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    report_type VARCHAR(100) NOT NULL,
    frequency VARCHAR(50) NOT NULL, -- Daily, Weekly, Monthly
    recipients TEXT[] NOT NULL,
    format VARCHAR(20) DEFAULT 'pdf',
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE report_schedules ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- COMMISSION MANAGEMENT (PRD 4)
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

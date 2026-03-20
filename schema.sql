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
    total_price DECIMAL(15,2) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
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
    
    status VARCHAR(50) DEFAULT 'unpaid' CHECK (status IN ('unpaid', 'partial', 'paid')),
    notes TEXT,
    
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
            WHERE invoice_id = NEW.invoice_id
        ),
        status = CASE
            WHEN (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id = NEW.invoice_id) >= amount THEN 'paid'
            WHEN (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id = NEW.invoice_id) > 0 THEN 'partial'
            ELSE 'unpaid'
        END,
        updated_at = NOW()
    WHERE id = NEW.invoice_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_payment_insert
AFTER INSERT ON payments
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

-- Service role has full access (used by your backend)
-- Frontend uses service role key only through the backend API

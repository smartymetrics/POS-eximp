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
    quantity: INTEGER DEFAULT 1,
    unit_price: DECIMAL(15,2) DEFAULT 0,
    
    amount: DECIMAL(15,2) NOT NULL,
    amount_paid DECIMAL(15,2) DEFAULT 0,
    balance_due DECIMAL(15,2) GENERATED ALWAYS AS (amount - amount_paid) STORED,
    
    payment_terms VARCHAR(100) DEFAULT 'Outright',  -- Outright / Installment
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    
    status VARCHAR(50) DEFAULT 'unpaid' CHECK (status IN ('unpaid', 'partial', 'paid', 'voided', 'overdue')),
    pipeline_stage VARCHAR(50) DEFAULT 'inspection' CHECK (pipeline_stage IN ('inspection', 'offer', 'contract', 'closed')),
    notes TEXT,
    
    -- New fields for PRD v2
    sales_rep_name VARCHAR(255),
    co_owner_name VARCHAR(255),
    co_owner_email VARCHAR(255),
    signature_url TEXT,
    contract_signature_url TEXT,
    contract_signature_method VARCHAR(20) DEFAULT 'drawn' CHECK (contract_signature_method IN ('drawn', 'uploaded')),
    contract_signed_at TIMESTAMPTZ,
    payment_proof_url TEXT,
    passport_photo_url TEXT,
    purchase_purpose VARCHAR(100),
    source VARCHAR(50) DEFAULT 'manual', -- manual / google_form
    custom_contract_html TEXT, -- Lawyer-edited contract body HTML (overrides template if set)
    custom_cover_html TEXT, -- Editable cover page wording HTML (overrides default cover if set)
    custom_lawfirm_name VARCHAR(255), -- Editable lawyer firm name
    custom_lawfirm_address TEXT, -- Editable lawyer firm address
    custom_execution_html TEXT, -- Editable execution page HTML

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
    created_by UUID REFERENCES admins(id),
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

-- ============================================================
-- MARKETING DASHBOARD (LEGENDARY - PRD 6)
-- ============================================================

-- 1. MARKETING CONTACTS (Leads + Clients)
CREATE TABLE IF NOT EXISTS marketing_contacts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id UUID REFERENCES clients(id), -- NULL for non-client leads
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(50),
  tags TEXT[], -- e.g. {'coinfield', 'hot-lead', 'vip'}
  source VARCHAR(100), -- 'ecoms_client', 'csv_import', 'manual', 'form'
  contact_type VARCHAR(50) DEFAULT 'lead' CHECK (contact_type IN ('client', 'lead')),
  is_subscribed BOOLEAN DEFAULT true,
  unsubscribed_at TIMESTAMPTZ,
  unsubscribe_reason TEXT,
  bounce_count INTEGER DEFAULT 0,
  is_bounced BOOLEAN DEFAULT false,
  bounced_at TIMESTAMPTZ,
  engagement_score INTEGER DEFAULT 0, -- 0-100
  last_opened_at TIMESTAMPTZ,
  last_clicked_at TIMESTAMPTZ,
  total_emails_received INTEGER DEFAULT 0,
  total_emails_opened INTEGER DEFAULT 0,
  total_emails_clicked INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_marketing_contacts_email ON marketing_contacts(email);
CREATE INDEX IF NOT EXISTS idx_marketing_contacts_subscribed ON marketing_contacts(is_subscribed) WHERE is_subscribed = true;
CREATE INDEX IF NOT EXISTS idx_marketing_contacts_score ON marketing_contacts(engagement_score DESC);
ALTER TABLE marketing_contacts ENABLE ROW LEVEL SECURITY;

-- 2. EMAIL CAMPAIGNS
CREATE TABLE IF NOT EXISTS email_campaigns (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  subject_a VARCHAR(500) NOT NULL,
  subject_b VARCHAR(500), -- NULL if not A/B test
  preview_text VARCHAR(500),
  from_name VARCHAR(255) DEFAULT 'Eximp & Cloves',
  from_email VARCHAR(255) DEFAULT 'hello@mail.eximps-cloves.com',
  reply_to VARCHAR(255) DEFAULT 'marketing@mail.eximps-cloves.com',
  bcc_email VARCHAR(255) DEFAULT 'marketing@mail.eximps-cloves.com', -- internal monitoring copy, never visible to recipients
  html_body_a TEXT NOT NULL,
  html_body_b TEXT,
  status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft','scheduled','sending','sent','paused','failed')),
  is_ab_test BOOLEAN DEFAULT false,
  scheduled_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  total_recipients INTEGER DEFAULT 0,
  total_sent INTEGER DEFAULT 0,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE email_campaigns ENABLE ROW LEVEL SECURITY;

-- 3. MARKETING SEGMENTS
CREATE TABLE IF NOT EXISTS marketing_segments (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  segment_type VARCHAR(20) DEFAULT 'dynamic' CHECK (segment_type IN ('dynamic', 'static')),
  filter_rules JSONB,
  contact_count INTEGER DEFAULT 0,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE marketing_segments ENABLE ROW LEVEL SECURITY;

-- 4. CAMPAIGN SEGMENTS (Join table)
CREATE TABLE IF NOT EXISTS campaign_segments (
  campaign_id UUID REFERENCES email_campaigns(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES marketing_segments(id),
  PRIMARY KEY (campaign_id, segment_id)
);

-- 5. CAMPAIGN RECIPIENTS (Tracking per person per campaign)
CREATE TABLE IF NOT EXISTS campaign_recipients (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  campaign_id UUID NOT NULL REFERENCES email_campaigns(id),
  contact_id UUID NOT NULL REFERENCES marketing_contacts(id),
  variant CHAR(1) DEFAULT 'A', -- A or B for A/B tests
  resend_message_id VARCHAR(255),
  status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending','sent','delivered','bounced','failed')),
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,       -- first open
  last_opened_at TIMESTAMPTZ,  -- most recent open
  open_count INTEGER DEFAULT 0,
  clicked_at TIMESTAMPTZ,      -- first click
  last_clicked_at TIMESTAMPTZ,
  click_count INTEGER DEFAULT 0,
  bounced_at TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ,
  spam_reported_at TIMESTAMPTZ,
  UNIQUE(campaign_id, contact_id)
);

-- 6. EMAIL CLICK EVENTS
CREATE TABLE IF NOT EXISTS email_click_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  campaign_id UUID NOT NULL REFERENCES email_campaigns(id),
  contact_id UUID NOT NULL REFERENCES marketing_contacts(id),
  original_url TEXT NOT NULL,
  clicked_at TIMESTAMPTZ DEFAULT NOW(),
  ip_address VARCHAR(50),
  user_agent TEXT
);

-- 7. MARKETING UNSUBSCRIBES (Suppression list)
CREATE TABLE IF NOT EXISTS marketing_unsubscribes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  contact_id UUID NOT NULL REFERENCES marketing_contacts(id),
  email VARCHAR(255) NOT NULL,
  campaign_id UUID REFERENCES email_campaigns(id), -- NULL if unsubscribed manually
  reason TEXT,
  unsubscribed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. MEDIA LIBRARY
CREATE TABLE IF NOT EXISTS media_library (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  filename VARCHAR(500) NOT NULL,
  original_filename VARCHAR(500),
  file_url TEXT NOT NULL,
  file_size INTEGER,
  mime_type VARCHAR(100),
  width INTEGER,
  height INTEGER,
  uploaded_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE media_library ENABLE ROW LEVEL SECURITY;
-- ============================================================
-- RLS POLICIES FOR MARKETING
-- ============================================================

-- Authenticated admins can do everything with marketing data
CREATE POLICY "Admins have full access to marketing_contacts" ON marketing_contacts FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to email_campaigns" ON email_campaigns FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to marketing_segments" ON marketing_segments FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to campaign_segments" ON campaign_segments FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to campaign_recipients" ON campaign_recipients FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to email_click_events" ON email_click_events FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to marketing_unsubscribes" ON marketing_unsubscribes FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to media_library" ON media_library FOR ALL TO authenticated USING (true);

-- ============================================================
-- SUPPORT HUB & TICKETING (PRD 8)
-- ============================================================

CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subject VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100), -- 'billing', 'property', 'contract', 'general'
    priority VARCHAR(50) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'pending', 'resolved', 'closed')),
    client_id UUID REFERENCES clients(id),
    contact_email VARCHAR(255), -- for non-client visitors
    contact_name VARCHAR(255),
    assigned_admin_id UUID REFERENCES admins(id),
    last_responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_responses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    admin_id UUID REFERENCES admins(id),
    is_internal BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_responses ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- MEETING SCHEDULER (PRD 8)
-- ============================================================

CREATE TABLE IF NOT EXISTS appointments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID REFERENCES clients(id),
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    property_id UUID REFERENCES properties(id),
    appointment_type VARCHAR(100) DEFAULT 'inspection', -- 'inspection', 'consultation', 'signing'
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'no_show')),
    medium VARCHAR(50) DEFAULT 'physical' CHECK (medium IN ('physical', 'virtual')),
    location TEXT, -- office or property address
    meeting_link TEXT, -- for virtual meetings
    notes TEXT,
    reminder_sent_at TIMESTAMPTZ,
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Migration 057: Cooperative Societies & Multi-Tenancy Module
-- Eximp & Cloves Infrastructure Limited
--
-- Features:
-- 1. Cooperatives table (Unregistered -> Registered Corporate KYC)
-- 2. Cooperative Admins (Max 3 admins per cooperative)
-- 3. Cooperative Members (Up to 1,000 members per society)
-- 4. Sub-Indexed Invoicing (EC-COP-XXXXXX and EC-COP-XXXXXX/YYY)
-- 5. Cooperative Receipts (RCP-COP-XXXXXX)
-- 6. Property Transfers (Ongoing payment plans & Fully paid transfers)
-- 7. Cooperative Activity & Audit Log (Immutable tracking of the 3 admins)
-- 8. Atomic Sequence Generators
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Cooperatives Master Table
CREATE TABLE IF NOT EXISTS cooperatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE,
    registration_status VARCHAR(50) DEFAULT 'unregistered' CHECK (registration_status IN ('unregistered', 'pending_kyc', 'registered', 'rejected')),
    onboarding_fee_paid BOOLEAN DEFAULT FALSE,
    onboarding_fee_amount DECIMAL(15, 2) DEFAULT 0.00,
    registration_number VARCHAR(100),
    registration_type VARCHAR(100), -- Ministry of Cooperatives, CAC, etc.
    registered_address TEXT,
    state VARCHAR(100),
    lga VARCHAR(100),
    official_email VARCHAR(255),
    official_phone VARCHAR(50),
    certificate_url TEXT,
    bye_laws_url TEXT,
    resolution_url TEXT,
    kyc_submitted_at TIMESTAMPTZ,
    kyc_reviewed_at TIMESTAMPTZ,
    kyc_reviewed_by UUID REFERENCES admins(id),
    kyc_rejection_reason TEXT,
    total_allocated_plots INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_cooperatives_status ON cooperatives(registration_status);
CREATE INDEX IF NOT EXISTS idx_cooperatives_code ON cooperatives(code);

-- 2. Cooperative Admins Table (Max 3 per cooperative)
CREATE TABLE IF NOT EXISTS cooperative_admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id UUID NOT NULL REFERENCES cooperatives(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin' CHECK (role IN ('president', 'secretary', 'treasurer', 'admin')),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coop_admins_coop ON cooperative_admins(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_coop_admins_email ON cooperative_admins(email);

-- 3. Cooperative Members Table (Up to 1,000 members per cooperative)
CREATE TABLE IF NOT EXISTS cooperative_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id UUID NOT NULL REFERENCES cooperatives(id) ON DELETE CASCADE,
    member_number VARCHAR(100), -- Society internal payroll/member ID
    sub_index INTEGER NOT NULL, -- Sequential plot index (1, 2, 3...)
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50) NOT NULL,
    residential_address TEXT,
    nin VARCHAR(20), -- National Identity Number (NO BVN)
    
    -- Next of Kin details
    nok_name VARCHAR(255),
    nok_phone VARCHAR(50),
    nok_relationship VARCHAR(100),
    nok_address TEXT,
    
    -- Verification Documents & Security Lock
    passport_photo_url TEXT,
    signature_url TEXT,
    passport_locked BOOLEAN DEFAULT FALSE,
    signature_locked BOOLEAN DEFAULT FALSE,
    passport_unlock_reason TEXT,
    signature_unlock_reason TEXT,
    
    -- Allocated Property
    property_id UUID REFERENCES properties(id),
    plot_number VARCHAR(100),
    block_number VARCHAR(100),
    plot_size_sqm DECIMAL(10, 2) DEFAULT 500.00,
    allocation_status VARCHAR(50) DEFAULT 'unallocated' CHECK (allocation_status IN ('unallocated', 'provisional', 'confirmed', 'transferred')),
    allocation_date DATE,
    provisional_letter_url TEXT,
    
    -- Member Portal Auth
    password_hash VARCHAR(255),
    is_portal_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    
    -- Notification Preferences
    notify_email BOOLEAN DEFAULT TRUE,
    notify_sms BOOLEAN DEFAULT TRUE,
    notify_whatsapp BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(cooperative_id, sub_index)
);

CREATE INDEX IF NOT EXISTS idx_coop_members_coop ON cooperative_members(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_coop_members_phone ON cooperative_members(phone);
CREATE INDEX IF NOT EXISTS idx_coop_members_email ON cooperative_members(email);
CREATE INDEX IF NOT EXISTS idx_coop_members_sub ON cooperative_members(cooperative_id, sub_index);

-- 4. Cooperative Master & Sub-Invoices Table
CREATE TABLE IF NOT EXISTS cooperative_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id UUID NOT NULL REFERENCES cooperatives(id) ON DELETE CASCADE,
    member_id UUID REFERENCES cooperative_members(id) ON DELETE SET NULL,
    
    -- Invoice Type: master (society deal) or sub (member allocation)
    invoice_type VARCHAR(20) DEFAULT 'sub' CHECK (invoice_type IN ('master', 'sub')),
    invoice_number VARCHAR(100) UNIQUE NOT NULL, -- e.g. EC-COP-000001 or EC-COP-000001/014
    parent_invoice_id UUID REFERENCES cooperative_invoices(id),
    
    sub_index INTEGER,
    property_id UUID REFERENCES properties(id),
    total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    amount_paid DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    balance_due DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    
    payment_plan VARCHAR(50) DEFAULT 'installments', -- outright, installments
    due_date DATE,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'partially_paid', 'paid', 'overdue', 'void')),
    
    pdf_url TEXT,
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coop_inv_num ON cooperative_invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_coop_inv_coop ON cooperative_invoices(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_coop_inv_member ON cooperative_invoices(member_id);

-- 5. Cooperative Payments Table (Receipts)
CREATE TABLE IF NOT EXISTS cooperative_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id UUID NOT NULL REFERENCES cooperatives(id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES cooperative_invoices(id),
    member_id UUID REFERENCES cooperative_members(id),
    
    receipt_number VARCHAR(100) UNIQUE NOT NULL, -- e.g. RCP-COP-000001
    amount DECIMAL(15, 2) NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'bank_transfer',
    payment_reference VARCHAR(100),
    proof_of_payment_url TEXT,
    payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    receipt_pdf_url TEXT,
    recorded_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coop_pay_rcp ON cooperative_payments(receipt_number);
CREATE INDEX IF NOT EXISTS idx_coop_pay_inv ON cooperative_payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_coop_pay_member ON cooperative_payments(member_id);

-- 6. Property Transfers Table
CREATE TABLE IF NOT EXISTS cooperative_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id UUID NOT NULL REFERENCES cooperatives(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES cooperative_members(id),
    invoice_id UUID REFERENCES cooperative_invoices(id),
    
    transfer_type VARCHAR(50) NOT NULL CHECK (transfer_type IN ('active_plan', 'fully_paid')),
    outstanding_balance DECIMAL(15, 2) DEFAULT 0.00,
    
    -- New Owner KYC
    new_owner_name VARCHAR(255) NOT NULL,
    new_owner_email VARCHAR(255),
    new_owner_phone VARCHAR(50) NOT NULL,
    new_owner_address TEXT,
    new_owner_nin VARCHAR(20),
    new_owner_nok_name VARCHAR(255),
    new_owner_nok_phone VARCHAR(50),
    new_owner_nok_relationship VARCHAR(100),
    new_owner_passport_url TEXT,
    new_owner_signature_url TEXT,
    
    -- Governance & Approvals
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'exco_approved', 'legal_approved', 'rejected', 'completed')),
    exco_approved_by UUID REFERENCES cooperative_admins(id),
    exco_approved_at TIMESTAMPTZ,
    legal_approved_by UUID REFERENCES admins(id),
    legal_approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    
    deed_of_transfer_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coop_transfers_coop ON cooperative_transfers(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_coop_transfers_member ON cooperative_transfers(member_id);

-- 7. Cooperative Activity & Audit Log (Tracks actions by the 3 admins)
CREATE TABLE IF NOT EXISTS cooperative_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id UUID NOT NULL REFERENCES cooperatives(id) ON DELETE CASCADE,
    admin_id UUID REFERENCES cooperative_admins(id),
    admin_name VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL, -- create_member, edit_member, delete_member, unlock_passport, approve_transfer, etc.
    target_entity VARCHAR(100), -- member, kyc, transfer, invoice
    target_id UUID,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coop_log_coop ON cooperative_activity_log(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_coop_log_admin ON cooperative_activity_log(admin_id);
CREATE INDEX IF NOT EXISTS idx_coop_log_created ON cooperative_activity_log(created_at DESC);

-- 8. Atomic Sequence Counters for Cooperative Invoices and Receipts
CREATE TABLE IF NOT EXISTS cooperative_sequences (
    sequence_type VARCHAR(50) PRIMARY KEY, -- 'invoice', 'receipt'
    current_value BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO cooperative_sequences (sequence_type, current_value)
VALUES ('invoice', 0), ('receipt', 0)
ON CONFLICT (sequence_type) DO NOTHING;

-- Function: Atomic Cooperative Invoice Number (EC-COP-000001)
CREATE OR REPLACE FUNCTION generate_coop_invoice_number()
RETURNS TEXT AS $$
DECLARE
    next_val BIGINT;
    formatted_num TEXT;
BEGIN
    UPDATE cooperative_sequences
    SET current_value = current_value + 1,
        updated_at = NOW()
    WHERE sequence_type = 'invoice'
    RETURNING current_value INTO next_val;

    formatted_num := 'EC-COP-' || LPAD(next_val::TEXT, 6, '0');
    RETURN formatted_num;
END;
$$ LANGUAGE plpgsql;

-- Function: Atomic Cooperative Receipt Number (RCP-COP-000001)
CREATE OR REPLACE FUNCTION generate_coop_receipt_number()
RETURNS TEXT AS $$
DECLARE
    next_val BIGINT;
    formatted_num TEXT;
BEGIN
    UPDATE cooperative_sequences
    SET current_value = current_value + 1,
        updated_at = NOW()
    WHERE sequence_type = 'receipt'
    RETURNING current_value INTO next_val;

    formatted_num := 'RCP-COP-' || LPAD(next_val::TEXT, 6, '0');
    RETURN formatted_num;
END;
$$ LANGUAGE plpgsql;


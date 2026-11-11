-- ============================================================
-- Migration 058: Cooperative Multi-Estate, Hybrid Subscriptions,
-- Dedicated Payment Verification Queue & Anti-Fraud Locks
-- Eximp & Cloves Infrastructure Limited
--
-- Features:
-- 1. cooperative_estate_schemes (Many-to-many entity-to-estate mapping with negotiated price tiers)
-- 2. cooperative_plot_allotments (Decoupled plot allocations per member with double-allocation unique index)
-- 3. cooperative_payments verification fields (Maker-checker bank verification queue)
-- 4. cooperative_members digital signature lifecycle & Evidence Act 2023 audit metadata
-- ============================================================

-- 1. Create cooperative_estate_schemes table
CREATE TABLE IF NOT EXISTS cooperative_estate_schemes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id UUID NOT NULL REFERENCES cooperatives(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    estate_code VARCHAR(50) DEFAULT 'EST',
    price_300sqm DECIMAL(15, 2) DEFAULT 0.00,
    price_500sqm DECIMAL(15, 2) DEFAULT 0.00,
    price_600sqm DECIMAL(15, 2) DEFAULT 0.00,
    price_custom DECIMAL(15, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(cooperative_id, property_id)
);

CREATE INDEX IF NOT EXISTS idx_coop_schemes_coop ON cooperative_estate_schemes(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_coop_schemes_prop ON cooperative_estate_schemes(property_id);

-- 2. Create cooperative_plot_allotments table
CREATE TABLE IF NOT EXISTS cooperative_plot_allotments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id UUID NOT NULL REFERENCES cooperatives(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES cooperative_members(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
    invoice_id UUID REFERENCES cooperative_invoices(id) ON DELETE SET NULL,
    plot_size_sqm DECIMAL(10, 2) NOT NULL DEFAULT 500.00,
    unit_number INTEGER DEFAULT 1,
    block_number VARCHAR(100),
    plot_number VARCHAR(100),
    allocation_status VARCHAR(50) DEFAULT 'unallocated' CHECK (allocation_status IN ('unallocated', 'provisional', 'confirmed', 'transferred')),
    allocation_date DATE,
    provisional_letter_url TEXT,
    deed_url TEXT,
    created_by_type VARCHAR(50) DEFAULT 'admin' CHECK (created_by_type IN ('admin', 'member_portal')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coop_allot_coop ON cooperative_plot_allotments(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_coop_allot_member ON cooperative_plot_allotments(member_id);
CREATE INDEX IF NOT EXISTS idx_coop_allot_prop ON cooperative_plot_allotments(property_id);
CREATE INDEX IF NOT EXISTS idx_coop_allot_inv ON cooperative_plot_allotments(invoice_id);

-- Double-Allocation Prevention: Partial Unique Index
CREATE UNIQUE INDEX IF NOT EXISTS uq_coop_estate_plot_allocation 
ON cooperative_plot_allotments (property_id, block_number, plot_number) 
WHERE allocation_status IN ('provisional', 'confirmed') 
  AND plot_number IS NOT NULL 
  AND block_number IS NOT NULL;

-- 3. Enhance cooperative_payments for Dedicated Verification Queue
ALTER TABLE cooperative_payments ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'confirmed';
ALTER TABLE cooperative_payments ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100);
ALTER TABLE cooperative_payments ADD COLUMN IF NOT EXISTS bank_session_id VARCHAR(100);
ALTER TABLE cooperative_payments ADD COLUMN IF NOT EXISTS verified_by UUID REFERENCES admins(id);
ALTER TABLE cooperative_payments ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
ALTER TABLE cooperative_payments ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_coop_payments_status ON cooperative_payments(status);

-- 4. Enhance cooperative_members for Signature Lifecycle & Evidence Act 2023
ALTER TABLE cooperative_members ADD COLUMN IF NOT EXISTS signature_status VARCHAR(50) DEFAULT 'unsigned';
ALTER TABLE cooperative_members ADD COLUMN IF NOT EXISTS signature_rejected_reason TEXT;
ALTER TABLE cooperative_members ADD COLUMN IF NOT EXISTS signature_requested_at TIMESTAMPTZ;
ALTER TABLE cooperative_members ADD COLUMN IF NOT EXISTS signing_ip VARCHAR(100);
ALTER TABLE cooperative_members ADD COLUMN IF NOT EXISTS signing_user_agent TEXT;
ALTER TABLE cooperative_members ADD COLUMN IF NOT EXISTS signing_token VARCHAR(255);
ALTER TABLE cooperative_members ADD COLUMN IF NOT EXISTS signing_audit_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_coop_members_sig_status ON cooperative_members(signature_status);


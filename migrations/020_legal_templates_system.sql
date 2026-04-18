-- Migration: Legal Templates System (Phase 1-6 Complete)
-- Date: April 2026
-- Purpose: Create tables for templates, signing, memos, and workflow

-- ────────────────────────────────────────────────────────────────
-- PHASE 1: TEMPLATE SYSTEM
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS legal_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Offer Letter', 'Employment Contract', 'NDA', 'Disciplinary Review', 'Other')),
    description TEXT,
    default_content_html TEXT,
    preview_html TEXT,
    created_by UUID REFERENCES admins(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS legal_template_variables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES legal_templates(id) ON DELETE CASCADE,
    var_name TEXT NOT NULL,
    var_label TEXT NOT NULL,
    var_type TEXT CHECK (var_type IN ('text', 'date', 'currency', 'number', 'enum', 'multiline')) DEFAULT 'text',
    required BOOLEAN DEFAULT FALSE,
    enum_values TEXT, -- JSON array for dropdown options
    placeholder TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- PHASE 4: DIGITAL SIGNING
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS legal_signing_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id UUID NOT NULL REFERENCES legal_matters(id) ON DELETE CASCADE,
    signing_token VARCHAR(255) UNIQUE NOT NULL,
    status TEXT CHECK (status IN ('Pending', 'Signed', 'Acknowledged', 'Rejected', 'Expired')) DEFAULT 'Pending',
    document_hash VARCHAR(255) NOT NULL,
    document_title TEXT,
    initiated_by UUID REFERENCES admins(id) ON DELETE SET NULL,
    initiated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    signed_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    signer_email TEXT,
    signer_name TEXT,
    signature_metadata JSONB,
    expiry_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '7 days',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- PHASE 3: MEMO THREAD
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS legal_matter_memos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id UUID NOT NULL REFERENCES legal_matters(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES admins(id) ON DELETE SET NULL,
    author_name TEXT,
    author_role TEXT,
    message_content TEXT NOT NULL,
    message_type TEXT CHECK (message_type IN ('note', 'status_change', 'file_upload', 'mention')) DEFAULT 'note',
    is_internal BOOLEAN DEFAULT TRUE, -- Private to HR/Legal only
    metadata JSONB, -- For attachments, mentions, etc
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- ENHANCE EXISTING TABLES
-- ────────────────────────────────────────────────────────────────

-- Add columns to legal_matters if they don't exist
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS template_used_id UUID REFERENCES legal_templates(id);
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS variables_used JSONB DEFAULT '{}';
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS signed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS signed_by TEXT;
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS signature_metadata JSONB;
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Draft' CHECK (status IN ('Draft', 'In-Progress', 'Legal Review', 'Legal Signing', 'Executed', 'Archived'));
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS requires_signing BOOLEAN DEFAULT TRUE;

-- ────────────────────────────────────────────────────────────────
-- INDEXES FOR PERFORMANCE
-- ────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_signing_requests_matter ON legal_signing_requests(matter_id);
CREATE INDEX IF NOT EXISTS idx_signing_requests_token ON legal_signing_requests(signing_token);
CREATE INDEX IF NOT EXISTS idx_signing_requests_status ON legal_signing_requests(status);
CREATE INDEX IF NOT EXISTS idx_memos_matter ON legal_matter_memos(matter_id);
CREATE INDEX IF NOT EXISTS idx_memos_author ON legal_matter_memos(author_id);
CREATE INDEX IF NOT EXISTS idx_templates_category ON legal_templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_active ON legal_templates(is_active);

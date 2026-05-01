-- Migration: Fix Signing Schema and Pipeline Constraints
-- Date: May 2026
-- Purpose: Resolve 400 Bad Request during client signing by adding missing audit columns and expanding pipeline stages.

-- 1. Add missing audit columns to invoices table
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS contract_audit_ip TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS contract_audit_agent TEXT;

-- 2. Expand pipeline_stage check constraint to include 'paid' and 'interest'
DO $$ 
BEGIN
    ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_pipeline_stage_check;
    ALTER TABLE invoices ADD CONSTRAINT invoices_pipeline_stage_check 
    CHECK (pipeline_stage IN ('inspection', 'interest', 'offer', 'contract', 'paid', 'closed'));
END $$;

-- 3. Expand contract_signature_method check constraint to accept 'draw' and 'upload' as well
DO $$ 
BEGIN
    ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_contract_signature_method_check;
    ALTER TABLE invoices ADD CONSTRAINT invoices_contract_signature_method_check 
    CHECK (contract_signature_method IN ('drawn', 'uploaded', 'draw', 'upload'));
END $$;

COMMENT ON COLUMN invoices.contract_audit_ip IS 'Captured IP address of the client at the time of signing.';
COMMENT ON COLUMN invoices.contract_audit_agent IS 'Captured User-Agent (browser/device) of the client at the time of signing.';

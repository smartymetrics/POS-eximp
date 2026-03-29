-- Migration: Add invoice contract signature fields
-- Date: 2026-03-29
-- Description: Adds separate contract signature storage for client contract execution

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS contract_signature_url TEXT;

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS contract_signature_method VARCHAR(20) DEFAULT 'drawn' CHECK (contract_signature_method IN ('drawn', 'uploaded'));

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS contract_signed_at TIMESTAMPTZ;

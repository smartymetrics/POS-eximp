-- =====================================================
-- MIGRATION: Add WHT Remittance Tracking to Commissions
-- Run this in your Supabase SQL Editor
-- =====================================================

ALTER TABLE commission_earnings
  ADD COLUMN IF NOT EXISTS is_wht_remitted BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS wht_remitted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS wht_receipt_ref TEXT;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_commission_earnings_wht_remittance 
ON commission_earnings(is_wht_remitted) 
WHERE is_wht_remitted = FALSE;

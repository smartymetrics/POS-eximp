-- =====================================================
-- MIGRATION: Expand Payroll Tracking for HRM
-- Run this in your Supabase SQL Editor
-- =====================================================

ALTER TABLE payroll_records
  ADD COLUMN IF NOT EXISTS nhf DECIMAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS employer_pension DECIMAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS net_pay_breakdown JSONB; -- For storing the detailed tax calculation

-- Update existing records if needed (set breakdown to empty)
UPDATE payroll_records SET net_pay_breakdown = '{}'::jsonb WHERE net_pay_breakdown IS NULL;

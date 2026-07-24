-- =====================================================
-- MIGRATION: Extend payout_batches for Partner Payouts
-- Run this in your Supabase SQL Editor
-- =====================================================

-- 1. Make sales_rep_id optional (remove NOT NULL constraint)
ALTER TABLE payout_batches
  ALTER COLUMN sales_rep_id DROP NOT NULL;

-- 2. Add vendor_id column for partner payouts
ALTER TABLE payout_batches
  ADD COLUMN IF NOT EXISTS vendor_id UUID REFERENCES vendors(id);

-- 3. Verify the changes
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'payout_batches'
ORDER BY ordinal_position;

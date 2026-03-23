-- Migration: Add partial payment tracking to commission_earnings
-- Run this in your Supabase SQL Editor

-- 1. Add amount_paid column to track how much has been paid per earning record
ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS amount_paid DECIMAL(15,2) NOT NULL DEFAULT 0.00;

-- 2. Sync existing fully-paid records so amount_paid reflects the true historical value
UPDATE commission_earnings 
SET amount_paid = final_amount 
WHERE is_paid = true AND amount_paid = 0;

-- 3. Useful index for querying partially paid records
CREATE INDEX IF NOT EXISTS idx_commission_earnings_partially_paid 
ON commission_earnings(sales_rep_id, is_paid) WHERE is_paid = false AND amount_paid > 0;

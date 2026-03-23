-- =====================================================================
-- PRD7: Backfill sales_rep_name on invoices
-- Run this in your Supabase SQL Editor.
-- This script updates invoices that are missing a sales_rep_name
-- by looking up the corresponding sales rep from commission_earnings.
-- =====================================================================

-- Step 1: Update invoices where sales_rep_name is NULL or empty
-- by joining to commission_earnings -> sales_reps
UPDATE invoices i
SET sales_rep_name = sr.name
FROM commission_earnings ce
JOIN sales_reps sr ON sr.id = ce.sales_rep_id
WHERE ce.invoice_id = i.id
  AND (i.sales_rep_name IS NULL OR i.sales_rep_name = '');

-- Step 2: Verify — check how many still have no sales rep name
SELECT
  count(*) FILTER (WHERE sales_rep_name IS NOT NULL AND sales_rep_name <> '') AS "With Sales Rep",
  count(*) FILTER (WHERE sales_rep_name IS NULL OR sales_rep_name = '') AS "Missing Sales Rep"
FROM invoices
WHERE status != 'voided';

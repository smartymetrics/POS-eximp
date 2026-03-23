-- =====================================================================
-- PRD8: Add sales_rep_id FK to invoices table
-- Run this in your Supabase SQL Editor.
-- =====================================================================

-- Step 1: Add the column
ALTER TABLE invoices
ADD COLUMN sales_rep_id UUID REFERENCES sales_reps(id) ON DELETE SET NULL;

-- Step 2: Backfill existing invoices where we know the rep from commission_earnings
UPDATE invoices i
SET sales_rep_id = ce.sales_rep_id
FROM commission_earnings ce
WHERE ce.invoice_id = i.id;

-- Step 3: Verify how many invoices now have a sales_rep_id vs how many are missing it
SELECT
  count(*) FILTER (WHERE sales_rep_id IS NOT NULL) AS "With Sales Rep ID",
  count(*) FILTER (WHERE sales_rep_id IS NULL AND sales_rep_name IS NOT NULL AND sales_rep_name <> '') AS "Has Name but NO ID",
  count(*) FILTER (WHERE sales_rep_id IS NULL AND (sales_rep_name IS NULL OR sales_rep_name = '')) AS "Completely Missing Rep"
FROM invoices
WHERE status != 'voided';

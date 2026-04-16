-- Fix invoices with invalid pipeline_stage or status (often caused by imports)
-- This ensures they satisfy CHECK constraints and can be updated during signing.

UPDATE invoices
SET pipeline_stage = 'contract'
WHERE pipeline_stage IS NULL OR pipeline_stage = '' OR pipeline_stage NOT IN ('inspection', 'offer', 'contract', 'closed');

UPDATE invoices
SET status = 'unpaid'
WHERE status IS NULL OR status = '' OR status NOT IN ('unpaid', 'partial', 'paid', 'voided', 'overdue');

-- Also ensure signature method is valid if present
UPDATE invoices
SET contract_signature_method = 'drawn'
WHERE contract_signature_method IS NOT NULL AND contract_signature_method NOT IN ('drawn', 'uploaded');

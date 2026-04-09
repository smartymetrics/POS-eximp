-- BACKFILL CLIENT ASSIGNMENTS AND STAGES
-- 1. Sync assigned_rep_id from the latest invoice
UPDATE clients c
SET assigned_rep_id = i.created_by
FROM (
    SELECT DISTINCT ON (client_id) client_id, created_by 
    FROM invoices 
    WHERE created_by IS NOT NULL
    ORDER BY client_id, created_at DESC
) i
WHERE c.id = i.client_id
AND c.assigned_rep_id IS NULL;

-- 2. Sync pipeline_stage based on invoice status
-- Closed: Clients with any 'paid' invoice
UPDATE clients
SET pipeline_stage = 'closed'
WHERE id IN (SELECT client_id FROM invoices WHERE status = 'paid')
AND (pipeline_stage IS NULL OR pipeline_stage = 'inspection');

-- Contract: Clients with any 'partial' or 'unpaid' invoice (and not already closed)
UPDATE clients
SET pipeline_stage = 'contract'
WHERE id IN (SELECT client_id FROM invoices WHERE status IN ('unpaid', 'partial'))
AND (pipeline_stage IS NULL OR pipeline_stage = 'inspection');

-- 3. Audit Log for the backfill
INSERT INTO activity_log (event_type, description, created_at)
VALUES ('data_migration', 'Backfilled client assignments and pipeline stages from historical invoices', NOW());

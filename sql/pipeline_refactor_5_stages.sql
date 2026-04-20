-- 5-Stage Sales Pipeline Refactor Migration
-- High-Focus Model: lead, nurturing, interest, paid, closed

BEGIN;

-- 1. DROP EXISTING CONSTRAINTS (Postgres auto-generated names)
-- We use a dynamic block to drop any check constraints on the pipeline_stage column
DO $$
DECLARE
    r RECORD;
BEGIN
    -- For clients table
    FOR r IN (
        SELECT constraint_name 
        FROM information_schema.constraint_column_usage 
        WHERE table_name = 'clients' AND column_name = 'pipeline_stage'
    ) LOOP
        EXECUTE 'ALTER TABLE clients DROP CONSTRAINT ' || quote_ident(r.constraint_name);
    END LOOP;

    -- For invoices table
    FOR r IN (
        SELECT constraint_name 
        FROM information_schema.constraint_column_usage 
        WHERE table_name = 'invoices' AND column_name = 'pipeline_stage'
    ) LOOP
        EXECUTE 'ALTER TABLE invoices DROP CONSTRAINT ' || quote_ident(r.constraint_name);
    END LOOP;
END $$;

-- 2. MIGRATE DATA
-- Mapping: inspection/offer -> interest, contract -> paid, closed -> closed
UPDATE clients SET pipeline_stage = 'interest' WHERE pipeline_stage IN ('inspection', 'offer');
UPDATE clients SET pipeline_stage = 'paid' WHERE pipeline_stage = 'contract';
-- closed remains closed

UPDATE invoices SET pipeline_stage = 'interest' WHERE pipeline_stage IN ('inspection', 'offer');
UPDATE invoices SET pipeline_stage = 'paid' WHERE pipeline_stage = 'contract';
-- closed remains closed

-- 3. UPDATE DEFAULTS
ALTER TABLE clients ALTER COLUMN pipeline_stage SET DEFAULT 'lead';
ALTER TABLE invoices ALTER COLUMN pipeline_stage SET DEFAULT 'lead';

-- 4. APPLY NEW CHECK CONSTRAINTS
ALTER TABLE clients ADD CONSTRAINT clients_pipeline_stage_check 
    CHECK (pipeline_stage IN ('lead', 'nurturing', 'interest', 'paid', 'closed'));

ALTER TABLE invoices ADD CONSTRAINT invoices_pipeline_stage_check 
    CHECK (pipeline_stage IN ('lead', 'nurturing', 'interest', 'paid', 'closed'));

COMMIT;

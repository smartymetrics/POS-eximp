-- GLOBAL SCHEMA ALIGNMENT FIX
-- Resolves inconsistencies where auth.users(id) was used instead of admins(id)
-- Also creates the missing marketing_events table needed for the Calendar Service.

-- 1. Create missing marketing_events table
CREATE TABLE IF NOT EXISTS marketing_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    event_date DATE NOT NULL,
    action TEXT,
    event_type TEXT DEFAULT 'custom',
    is_recurring BOOLEAN DEFAULT FALSE,
    frequency TEXT CHECK (frequency IN ('weekly', 'monthly', 'yearly')),
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES admins(id)
);

CREATE INDEX IF NOT EXISTS idx_marketing_events_date ON marketing_events(event_date);

-- 2. Audit and Fix Foreign Keys (Migrate from auth.users to admins)
-- Note: This script is idempotent and can be run multiple times safely.

DO $$ 
BEGIN
    -- Fix properties.owner_agent_id
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'properties' AND column_name = 'owner_agent_id') THEN
        IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_name = 'properties' AND constraint_type = 'FOREIGN KEY' AND constraint_name = 'properties_owner_agent_id_fkey') THEN
            ALTER TABLE properties DROP CONSTRAINT properties_owner_agent_id_fkey;
        END IF;
        ALTER TABLE properties ADD CONSTRAINT properties_owner_agent_id_fkey FOREIGN KEY (owner_agent_id) REFERENCES admins(id);
        RAISE NOTICE 'Fixed properties.owner_agent_id foreign key.';
    END IF;

    -- Fix documents.created_by
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'created_by') THEN
        IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_name = 'documents' AND constraint_type = 'FOREIGN KEY' AND constraint_name = 'documents_created_by_fkey') THEN
            ALTER TABLE documents DROP CONSTRAINT documents_created_by_fkey;
        END IF;
        ALTER TABLE documents ADD CONSTRAINT documents_created_by_fkey FOREIGN KEY (created_by) REFERENCES admins(id);
        RAISE NOTICE 'Fixed documents.created_by foreign key.';
    END IF;

    -- Fix campaigns.created_by
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'campaigns' AND column_name = 'created_by') THEN
        IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_name = 'campaigns' AND constraint_type = 'FOREIGN KEY' AND constraint_name = 'campaigns_created_by_fkey') THEN
            ALTER TABLE campaigns DROP CONSTRAINT campaigns_created_by_fkey;
        END IF;
        ALTER TABLE campaigns ADD CONSTRAINT campaigns_created_by_fkey FOREIGN KEY (created_by) REFERENCES admins(id);
        RAISE NOTICE 'Fixed campaigns.created_by foreign key.';
    END IF;
END $$;

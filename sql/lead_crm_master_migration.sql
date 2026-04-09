-- Migration for Lead Management, RBAC, and Multimedia Support
ALTER TABLE clients 
ADD COLUMN IF NOT EXISTS pipeline_stage VARCHAR(50) DEFAULT 'inspection' CHECK (pipeline_stage IN ('inspection', 'offer', 'contract', 'closed')),
ADD COLUMN IF NOT EXISTS estimated_value DECIMAL(15,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS assigned_rep_id UUID REFERENCES admins(id);

ALTER TABLE ticket_responses
ADD COLUMN IF NOT EXISTS attachment_url TEXT;

ALTER TABLE activity_log
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_clients_assigned_rep ON clients(assigned_rep_id);
CREATE INDEX IF NOT EXISTS idx_clients_pipeline_stage ON clients(pipeline_stage);

-- Comments for reference
COMMENT ON COLUMN clients.pipeline_stage IS 'Current stage in the sales funnel';
COMMENT ON COLUMN clients.estimated_value IS 'Potential deal value for this lead';
COMMENT ON COLUMN clients.assigned_rep_id IS 'Sales Rep responsible for this lead';

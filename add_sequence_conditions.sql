-- Add conditional logic to sequence steps
ALTER TABLE sequence_steps 
ADD COLUMN IF NOT EXISTS requires_interaction BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS interaction_type VARCHAR(50) CHECK (interaction_type IN ('open', 'click')),
ADD COLUMN IF NOT EXISTS skip_if_not_met BOOLEAN DEFAULT TRUE;

-- Add "exited" status to enrollments
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'enrollment_status') THEN
        -- We just use VARCHAR(50) check constraint instead of TYPE to avoid migration issues
        ALTER TABLE contact_sequence_status DROP CONSTRAINT IF EXISTS contact_sequence_status_status_check;
        ALTER TABLE contact_sequence_status ADD CONSTRAINT contact_sequence_status_status_check 
            CHECK (status IN ('active', 'completed', 'paused', 'exited'));
    END IF;
END $$;

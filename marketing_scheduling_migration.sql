-- Add scheduling support to email_campaigns
ALTER TABLE public.email_campaigns 
ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS target_config JSONB;

-- Comment for clarity
COMMENT ON COLUMN public.email_campaigns.scheduled_for IS 'The intended future date and time to start the broadcast.';
COMMENT ON COLUMN public.email_campaigns.target_config IS 'Stores segments or manual email lists for scheduled broadcasts.';

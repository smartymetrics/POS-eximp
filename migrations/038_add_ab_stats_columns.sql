ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS variant_a_opens INTEGER DEFAULT 0;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS variant_b_opens INTEGER DEFAULT 0;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS variant_a_clicks INTEGER DEFAULT 0;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS variant_b_clicks INTEGER DEFAULT 0;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS variant_a_sent INTEGER DEFAULT 0;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS variant_b_sent INTEGER DEFAULT 0;

-- RPC for atomic increments of variant columns
CREATE OR REPLACE FUNCTION increment_campaign_variant_stats(camp_id UUID, col_name TEXT)
RETURNS void AS $$
BEGIN
    EXECUTE format('UPDATE email_campaigns SET %I = COALESCE(%I, 0) + 1 WHERE id = %L', col_name, col_name, camp_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

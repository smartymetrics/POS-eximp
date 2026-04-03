-- ============================================================
-- ECOMS - PRD 6: Marketing Analytics Enrichment
-- ============================================================

-- 1. ADAPT EMAIL_CAMPAIGNS Table
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS total_opens INTEGER DEFAULT 0;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS total_clicks INTEGER DEFAULT 0;

-- 2. STORED FUNCTION: increment_campaign_stats
-- Atomically increments total_opens or total_clicks for a campaign
CREATE OR REPLACE FUNCTION increment_campaign_stats(camp_id UUID, event_type TEXT)
RETURNS VOID AS $$
BEGIN
    IF event_type = 'open' THEN
        UPDATE email_campaigns 
        SET total_opens = total_opens + 1 
        WHERE id = camp_id;
    ELSIF event_type = 'click' THEN
        UPDATE email_campaigns 
        SET total_clicks = total_clicks + 1 
        WHERE id = camp_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. STORED FUNCTION: increment_contact_stats
-- Atomically increments total_emails_opened or total_emails_clicked for a contact
-- and updates the last activity timestamp.
CREATE OR REPLACE FUNCTION increment_contact_stats(cont_id UUID, event_type TEXT)
RETURNS VOID AS $$
BEGIN
    IF event_type = 'open' THEN
        UPDATE marketing_contacts 
        SET total_emails_opened = total_emails_opened + 1,
            last_opened_at = NOW(),
            updated_at = NOW()
        WHERE id = cont_id;
    ELSIF event_type = 'click' THEN
        UPDATE marketing_contacts 
        SET total_emails_clicked = total_emails_clicked + 1,
            last_clicked_at = NOW(),
            updated_at = NOW()
        WHERE id = cont_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Re-sync indexes (optional but good)
CREATE INDEX IF NOT EXISTS idx_email_campaigns_status ON email_campaigns(status);

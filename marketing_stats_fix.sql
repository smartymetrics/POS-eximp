-- ============================================================
-- ECOMS - Marketing Stats & Tracking Fix
-- Run this in your Supabase SQL Editor if stats are showing 0
-- ============================================================

-- 1. Ensure columns exist for Campaign Stats
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS total_opens INTEGER DEFAULT 0;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS total_clicks INTEGER DEFAULT 0;

-- 2. Ensure columns exist for Contact Stats
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS total_emails_opened INTEGER DEFAULT 0;
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS total_emails_clicked INTEGER DEFAULT 0;
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS engagement_score INTEGER DEFAULT 0;

-- 3. FUNCTION: increment_campaign_stats
CREATE OR REPLACE FUNCTION increment_campaign_stats(camp_id UUID, event_type TEXT)
RETURNS VOID AS $$
BEGIN
    IF event_type = 'open' THEN
        UPDATE email_campaigns SET total_opens = total_opens + 1 WHERE id = camp_id;
    ELSIF event_type = 'click' THEN
        UPDATE email_campaigns SET total_clicks = total_clicks + 1 WHERE id = camp_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. FUNCTION: increment_contact_stats
CREATE OR REPLACE FUNCTION increment_contact_stats(cont_id UUID, event_type TEXT)
RETURNS VOID AS $$
BEGIN
    IF event_type = 'open' THEN
        UPDATE marketing_contacts 
        SET total_emails_opened = total_emails_opened + 1, last_opened_at = NOW()
        WHERE id = cont_id;
    ELSIF event_type = 'click' THEN
        UPDATE marketing_contacts 
        SET total_emails_clicked = total_emails_clicked + 1, last_clicked_at = NOW()
        WHERE id = cont_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. FUNCTION: increment_engagement_score
CREATE OR REPLACE FUNCTION increment_engagement_score(cid UUID, amount INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE marketing_contacts 
    SET engagement_score = LEAST(100, engagement_score + amount)
    WHERE id = cid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

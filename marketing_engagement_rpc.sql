-- ============================================================
-- ECOMS - Marketing Score Logic
-- Run this in your Supabase SQL Editor
-- ============================================================

CREATE OR REPLACE FUNCTION increment_engagement_score(cid UUID, amount INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE marketing_contacts 
    SET engagement_score = LEAST(100, engagement_score + amount),
        updated_at = NOW()
    WHERE id = cid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

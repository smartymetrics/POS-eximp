-- ECOMS - Nightly Marketing Engagement Decay
CREATE OR REPLACE FUNCTION bulk_decay_engagement()
RETURNS VOID AS $$
DECLARE
    limit_180 TIMESTAMPTZ := NOW() - INTERVAL '180 days';
    limit_90 TIMESTAMPTZ := NOW() - INTERVAL '90 days';
    limit_30 TIMESTAMPTZ := NOW() - INTERVAL '30 days';
BEGIN
    -- Case 1: 180 Days Inactivity -> 0
    UPDATE marketing_contacts
    SET engagement_score = 0
    WHERE engagement_score > 0
      AND COALESCE(last_opened_at, created_at) < limit_180
      AND COALESCE(last_clicked_at, created_at) < limit_180;

    -- Case 2: 90 Days Inactivity -> Halve (only those not affected by Case 1)
    UPDATE marketing_contacts
    SET engagement_score = engagement_score / 2
    WHERE engagement_score > 0
      AND COALESCE(last_opened_at, created_at) < limit_90
      AND COALESCE(last_clicked_at, created_at) < limit_90
      AND (COALESCE(last_opened_at, created_at) >= limit_180 OR COALESCE(last_clicked_at, created_at) >= limit_180);

    -- Case 3: 30 Days Inactivity -> -5 (only those not affected by Case 1 or 2)
    UPDATE marketing_contacts
    SET engagement_score = GREATEST(0, engagement_score - 5)
    WHERE engagement_score > 0
      AND COALESCE(last_opened_at, created_at) < limit_30
      AND COALESCE(last_clicked_at, created_at) < limit_30
      AND (COALESCE(last_opened_at, created_at) >= limit_90 OR COALESCE(last_clicked_at, created_at) >= limit_90);

END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

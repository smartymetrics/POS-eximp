-- ============================================================
-- LINK SUBSCRIPTIONS TO VERIFICATIONS
-- ============================================================

-- Add subscription_id column to pending_verifications
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='pending_verifications' AND column_name='subscription_id') THEN
        ALTER TABLE pending_verifications ADD COLUMN subscription_id UUID REFERENCES property_subscriptions(id);
    END IF;
END $$;

-- Optional: Index for performance
CREATE INDEX IF NOT EXISTS idx_pending_verifications_subscription ON pending_verifications(subscription_id);

-- Refresh Schema Cache
NOTIFY pgrst, 'reload schema';

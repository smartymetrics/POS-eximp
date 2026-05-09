-- ══════════════════════════════════════════════════════════════════
--  Migration 049: Legal Notifications System
--  Enables: targeted alerts to lawyers, HR, and collaborators.
--  Lawyers only see contracts they're explicitly invited to.
--  Staff only see contracts where staff_visible = true.
-- ══════════════════════════════════════════════════════════════════

-- 1. legal_notifications table
CREATE TABLE IF NOT EXISTS legal_notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id    UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    matter_id       UUID REFERENCES legal_matters(id) ON DELETE CASCADE,
    type            TEXT NOT NULL DEFAULT 'system',
                    -- Values: invite | contract | signing | executed | visibility | memo | system
    title           TEXT NOT NULL,
    message         TEXT,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for fast per-user lookups
CREATE INDEX IF NOT EXISTS idx_legal_notif_recipient ON legal_notifications(recipient_id);
CREATE INDEX IF NOT EXISTS idx_legal_notif_matter    ON legal_notifications(matter_id);
CREATE INDEX IF NOT EXISTS idx_legal_notif_is_read   ON legal_notifications(recipient_id, is_read);

-- 2. Ensure legal_matters has staff_visible (backfill from migration 022)
ALTER TABLE legal_matters
    ADD COLUMN IF NOT EXISTS staff_visible BOOLEAN NOT NULL DEFAULT FALSE;

-- 3. hr_memo column on legal_matters (in case it's missing)
ALTER TABLE legal_matters
    ADD COLUMN IF NOT EXISTS hr_memo TEXT;

-- 4. external_party columns (in case earlier migration didn't add them)
ALTER TABLE legal_matters
    ADD COLUMN IF NOT EXISTS external_party_name  TEXT,
    ADD COLUMN IF NOT EXISTS external_party_email TEXT;

-- 5. invitation_note on legal_matter_collaborators
ALTER TABLE legal_matter_collaborators
    ADD COLUMN IF NOT EXISTS invitation_note TEXT;

-- 6. RLS policies (Supabase) — recipients can only see their own notifications
ALTER TABLE legal_notifications ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (used by FastAPI backend)
CREATE POLICY "service_role_all_legal_notifications"
    ON legal_notifications FOR ALL
    TO service_role USING (true) WITH CHECK (true);

-- Authenticated users may only select their own notifications
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'legal_notifications'
        AND policyname = 'user_read_own_notifications'
    ) THEN
        CREATE POLICY "user_read_own_notifications"
            ON legal_notifications FOR SELECT
            TO authenticated
            USING (recipient_id = auth.uid());
    END IF;
END $$;

-- ══════════════════════════════════════════════════════════════════
--  Seed: example notification types for reference
--  (Do NOT run in production — dev/documentation only)
-- ══════════════════════════════════════════════════════════════════
-- INSERT INTO legal_notifications (recipient_id, type, title, message, matter_id)
-- VALUES
--   ('<lawyer-uuid>', 'invite',   '⚖️ You have been invited to collaborate', 'HR has invited you to: Employment Contract – Jane Doe', '<matter-uuid>'),
--   ('<hr-uuid>',    'signing',   '✍️ Signing dispatched',                   'Contract sent to recipient for signature.',              '<matter-uuid>'),
--   ('<lawyer-uuid>','executed',  '✅ Contract executed',                     'All parties have signed.',                               '<matter-uuid>');


-- ══════════════════════════════════════════════════════════════════
--  ACCESS CONTROL: Invitation-gated RLS on legal_matters
--  Belt-and-suspenders enforcement at the DB level.
--  Even if the API has a bug, the DB will refuse unauthorised reads.
-- ══════════════════════════════════════════════════════════════════

-- Enable RLS on legal_matters (may already be on)
ALTER TABLE legal_matters ENABLE ROW LEVEL SECURITY;

-- Service role (FastAPI) — full access always (we enforce in code)
CREATE POLICY IF NOT EXISTS "service_role_all_legal_matters"
    ON legal_matters FOR ALL
    TO service_role USING (true) WITH CHECK (true);

-- View policy: authenticated portal users can only read:
--   (a) matters they drafted, OR
--   (b) matters they were explicitly invited to as a collaborator
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'legal_matters'
        AND policyname = 'invitation_gated_select'
    ) THEN
        CREATE POLICY "invitation_gated_select"
            ON legal_matters FOR SELECT
            TO authenticated
            USING (
                -- Drafter always sees their own
                drafter_id = auth.uid()
                OR
                -- Invited collaborator
                EXISTS (
                    SELECT 1 FROM legal_matter_collaborators lmc
                    WHERE lmc.matter_id = legal_matters.id
                    AND   lmc.admin_id  = auth.uid()
                )
                OR
                -- Staff seeing their own public contract
                (staff_id = auth.uid() AND staff_visible = TRUE)
            );
    END IF;
END $$;

-- Note: super_admin / admin access is handled by the service_role policy
-- (the API runs as service_role and applies its own super_admin logic).
-- Direct DB authenticated connections (e.g., Supabase dashboard) respect
-- the invitation_gated_select policy for safety.
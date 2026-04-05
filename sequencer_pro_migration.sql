-- ============================================================
-- EXIMP & CLOVES — SEQUENCER PRO MIGRATION
-- Run this once in your Supabase SQL Editor
-- ============================================================

-- 1. Add Smart Branching columns to sequence_steps
--    These power the "Only send if they opened the previous email" feature.
ALTER TABLE public.sequence_steps
    ADD COLUMN IF NOT EXISTS requires_interaction BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS interaction_type     VARCHAR(20)  DEFAULT 'open',  -- 'open' or 'click'
    ADD COLUMN IF NOT EXISTS skip_if_not_met      BOOLEAN DEFAULT FALSE;

-- 2. The contact_sequence_status table uses 'exited' as a status
--    (e.g. when a lead becomes a client mid-sequence).
--    The existing CHECK constraint may not allow it — this update
--    ensures the 'exited' value is accepted without error.
--    (If there is no CHECK constraint on the column, this is a no-op and harmless.)
ALTER TABLE public.contact_sequence_status
    DROP CONSTRAINT IF EXISTS contact_sequence_status_status_check;

-- Verify everything looks correct
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name IN ('sequence_steps', 'contact_sequence_status')
  AND table_schema = 'public'
ORDER BY table_name, ordinal_position;

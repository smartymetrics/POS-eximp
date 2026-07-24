-- Migration: Enhance procurement_expenses with payment tracking and draft links
-- Description: Adds payment status tracking and linking to estate drafts

ALTER TABLE procurement_expenses 
ADD COLUMN IF NOT EXISTS estate_draft_id UUID REFERENCES estate_drafts(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS amount_paid DECIMAL(15, 2) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'paid'; -- Defaulting to paid for existing legacy logs

-- Add index for draft performance
CREATE INDEX IF NOT EXISTS idx_procurement_draft ON procurement_expenses(estate_draft_id);

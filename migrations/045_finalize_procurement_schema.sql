-- Migration: Finalize procurement schema and fix cache issues
-- Description: Ensures all required columns for payment tracking and metadata are present

ALTER TABLE procurement_expenses 
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES admins(id),
ADD COLUMN IF NOT EXISTS estate_draft_id UUID REFERENCES estate_drafts(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS amount_paid DECIMAL(15, 2) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Refresh PostgREST schema cache (Supabase specific)
NOTIFY pgrst, 'reload schema';

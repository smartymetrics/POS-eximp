-- Migration 053: Add attachments column to procurement_submissions
-- Purpose: Store multiple supporting document URLs (JSONB array)

ALTER TABLE public.procurement_submissions 
ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]';

-- Update documentation
COMMENT ON COLUMN public.procurement_submissions.attachments IS 'Array of file paths/URLs for supporting documents';

-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload schema';

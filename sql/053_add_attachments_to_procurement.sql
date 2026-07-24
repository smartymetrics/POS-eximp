-- Add attachments column to procurement_submissions
ALTER TABLE procurement_submissions ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb;

-- Add attachments column to procurement_expenses (for fanned-out items)
ALTER TABLE procurement_expenses ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb;

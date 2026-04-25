
-- Migration: Add rejection_reason to expenditure_requests
-- Description: Standardizes rejection notes and stops overloading wht_exemption_reason.

ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- Optional: Migrate existing rejection reasons from wht_exemption_reason
-- Only if the status is 'rejected' and it looks like a rejection note rather than an exemption reason.
-- For safety, we'll leave existing data as is or only migrate if explicitly asked, 
-- but this SQL provides the column for future use.

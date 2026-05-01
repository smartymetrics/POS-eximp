-- Add client_type column to clients table to distinguish leads from paying customers
ALTER TABLE clients ADD COLUMN IF NOT EXISTS client_type TEXT DEFAULT 'lead';

-- Retroactively update existing clients who have a history of invoices, payments, or verifications
-- This ensures that established customers are correctly categorized as 'client'
UPDATE clients 
SET client_type = 'client' 
WHERE id IN (
    SELECT DISTINCT client_id FROM invoices
) OR id IN (
    SELECT DISTINCT client_id FROM payments
) OR id IN (
    SELECT DISTINCT client_id FROM pending_verifications
);

-- Ensure all future inserts default to 'lead' (already handled by DEFAULT 'lead')
COMMENT ON COLUMN clients.client_type IS 'Distinguishes between prospects (lead) and actual customers (client).';

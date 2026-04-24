-- Migration: Add category column to expenditure_requests
ALTER TABLE expenditure_requests ADD COLUMN category TEXT DEFAULT 'General';

-- Retroactively categorize existing records based on title or source
UPDATE expenditure_requests SET category = 'Sales Commission' WHERE title ILIKE '%commission%';
UPDATE expenditure_requests SET category = 'Office Expenditure' WHERE title ILIKE '%office%';
UPDATE expenditure_requests SET category = 'Partner Payout' WHERE title ILIKE '%partner%';

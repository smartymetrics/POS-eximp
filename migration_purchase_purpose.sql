-- Add Purchase Purpose column to invoices to track compliance refund exceptions

ALTER TABLE invoices ADD COLUMN purchase_purpose VARCHAR(50);

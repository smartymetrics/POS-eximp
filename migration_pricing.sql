-- Migration to add unit_price and quantity to invoices table
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS unit_price DECIMAL(15,2) DEFAULT 0;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS quantity INTEGER DEFAULT 1;

-- Update existing records to have a unit_price (amount / quantity)
-- For existing invoices, we'll assume quantity = 1 if not set
UPDATE invoices SET unit_price = amount / COALESCE(quantity, 1) WHERE unit_price = 0 OR unit_price IS NULL;

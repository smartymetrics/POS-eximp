-- Add a dedicated contract_closed flag to invoices so legal close status is tracked separately from sales pipeline stage.
ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS contract_closed BOOLEAN DEFAULT FALSE;

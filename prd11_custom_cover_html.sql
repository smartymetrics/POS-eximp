-- Add custom cover page editable text 
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS custom_cover_html TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS custom_lawfirm_name VARCHAR(255);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS custom_lawfirm_address TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS custom_execution_html TEXT;

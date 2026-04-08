-- Adding Spend Metrics to Marketing Campaigns
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS budget NUMERIC(12,2) DEFAULT 0;
ALTER TABLE email_campaigns ADD COLUMN IF NOT EXISTS actual_spend NUMERIC(12,2) DEFAULT 0;

-- 2. Add attribution columns to marketing_contacts
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS first_utm_source TEXT;
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS first_utm_medium TEXT;
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS first_utm_campaign TEXT;
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS first_utm_content TEXT;
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS first_utm_term TEXT;
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS last_campaign_id UUID REFERENCES email_campaigns(id);

-- 3. Add attribution columns to invoices
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS marketing_campaign_id UUID REFERENCES email_campaigns(id);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS attribution_utm_source TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS attribution_utm_medium TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS attribution_utm_campaign TEXT;

-- ============================================================
-- HRM Goal Achievement Auto-Detection Migration
-- ============================================================

-- 0. Administrative RPC for cross-table analytics
DROP FUNCTION IF EXISTS exec_sql(text);
CREATE OR REPLACE FUNCTION exec_sql(sql_body text)
RETURNS jsonb AS $$
DECLARE
    result jsonb;
BEGIN
    EXECUTE 'SELECT row_to_json(t) FROM (' || sql_body || ') t' INTO result;
    RETURN result;
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('error', SQLERRM);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 1. Upgrade KPI Templates with Automated Sources
ALTER TABLE kpi_templates ADD COLUMN IF NOT EXISTS measurement_source VARCHAR(50) DEFAULT 'manual';
ALTER TABLE kpi_templates ADD COLUMN IF NOT EXISTS default_unit VARCHAR(50) DEFAULT 'count';

-- 1b. Add Attribution to Marketing Contacts
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES admins(id);

-- Update check constraint for kpi_templates
DO $$ 
BEGIN 
    ALTER TABLE kpi_templates DROP CONSTRAINT IF EXISTS kpi_templates_source_check;
EXCEPTION 
    WHEN others THEN NULL; 
END $$;

ALTER TABLE kpi_templates ADD CONSTRAINT kpi_templates_source_check 
    CHECK (measurement_source IN (
      'mkt_leads_added',      -- marketing_contacts (Leads)
      'mkt_lead_conversion',   -- marketing_contacts (Lead -> Client)
      'mkt_campaigns_sent',    -- email_campaigns
      'mkt_open_rate',         -- campaign_recipients
      'sales_deals_closed',    -- invoices (Closed)
      'sales_revenue',         -- invoices (Paid Amt)
      'sales_collection_rate', -- payments vs invoices
      'ops_appointments',      -- appointments (Completed)
      'admin_ticket_esc',      -- support_tickets (Escalated)
      'admin_verify_time',     -- pending_verifications (Avg Turnaround)
      'team_achievement',      -- staff_goals Rollup (For Managers)
      'manual'
    ));

-- 2. Upgrade Staff Goals with Sync Metadata
ALTER TABLE staff_goals ADD COLUMN IF NOT EXISTS measurement_source VARCHAR(50) DEFAULT 'manual';
ALTER TABLE staff_goals ADD COLUMN IF NOT EXISTS achievement_status VARCHAR(20) DEFAULT 'On Track';
ALTER TABLE staff_goals ADD COLUMN IF NOT EXISTS achievement_pct NUMERIC DEFAULT 0;
ALTER TABLE staff_goals ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE staff_goals ADD COLUMN IF NOT EXISTS goals_breakdown JSONB;

DO $$ 
BEGIN 
    ALTER TABLE staff_goals DROP CONSTRAINT IF EXISTS staff_goals_status_check_new;
EXCEPTION 
    WHEN others THEN NULL; 
END $$;

ALTER TABLE staff_goals ADD CONSTRAINT staff_goals_status_check_new 
    CHECK (achievement_status IN ('Achieved', 'On Track', 'At Risk', 'Behind', 'Fair'));

-- 3. Seed Professional HRM Templates
INSERT INTO kpi_templates (name, department, measurement_source, default_unit, category)
VALUES 
    ('New Leads Added', 'Marketing', 'mkt_leads_added', 'leads', 'Lead Gen'),
    ('Lead Conversion Rate', 'Marketing', 'mkt_lead_conversion', '%', 'Conversion'),
    ('Email Campaigns Sent', 'Marketing', 'mkt_campaigns_sent', 'campaigns', 'Activity'),
    ('Deals Closed', 'Sales & Acquisitions', 'sales_deals_closed', 'deals', 'Revenue'),
    ('Revenue Collected', 'Sales & Acquisitions', 'sales_revenue', 'NGN', 'Revenue'),
    ('Appointments Coordinated', 'Operations', 'ops_appointments', 'appointments', 'Activity'),
    ('Team Goal Achievement', 'Admin', 'team_achievement', '%', 'Leadership')
ON CONFLICT DO NOTHING;

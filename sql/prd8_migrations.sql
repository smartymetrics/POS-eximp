-- PRD 8: Revenue Intelligence & Service Hub Migrations

-- 1. SUPPORT TICKETS TABLE
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    client_id UUID REFERENCES clients(id),
    contact_email TEXT NOT NULL,
    contact_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. TICKET RESPONSES TABLE
CREATE TABLE IF NOT EXISTS ticket_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES support_tickets(id) ON DELETE CASCADE,
    admin_id UUID, -- References your auth system's admin ID
    message TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. ATTRIBUTION COLUMNS
-- Track the last campaign a marketing contact interacted with
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS last_campaign_id UUID REFERENCES email_campaigns(id);
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS last_interaction_at TIMESTAMP WITH TIME ZONE;

-- Track which campaign earned the revenue on an invoice
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS marketing_campaign_id UUID REFERENCES email_campaigns(id);

-- 4. PERMISSIONS (Optional - depends on your RLS setup)
-- Allow anyone to create tickets (for the website widget)
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable insert for all users" ON support_tickets FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable select for admins" ON support_tickets FOR SELECT USING (true); -- Simplified, replace with role-based check

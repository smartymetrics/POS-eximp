-- ============================================================
-- MARKETING AUTOMATION (ACTIVE CAMPAIGN STYLE)
-- ============================================================

-- 1. Sequences Table
CREATE TABLE IF NOT EXISTS marketing_sequences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_event VARCHAR(100) NOT NULL, -- 'client_created', 'lead_tagged', 'manual'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Sequence Steps (The Drip Logic)
CREATE TABLE IF NOT EXISTS sequence_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sequence_id UUID REFERENCES marketing_sequences(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    delay_days INTEGER DEFAULT 0, -- Days to wait after enrollment or previous step
    campaign_id UUID REFERENCES email_campaigns(id), -- Uses a campaign as a template
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Contact Sequence Status (Tracking enrollment)
CREATE TABLE IF NOT EXISTS contact_sequence_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID REFERENCES marketing_contacts(id) ON DELETE CASCADE,
    sequence_id UUID REFERENCES marketing_sequences(id) ON DELETE CASCADE,
    current_step INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'completed', 'paused'
    next_send_date DATE, -- Calculated date for the next email
    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
    last_step_at TIMESTAMPTZ,
    UNIQUE(contact_id, sequence_id)
);

-- RLS
ALTER TABLE marketing_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE sequence_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_sequence_status ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins have full access to sequences" ON marketing_sequences FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to sequence steps" ON sequence_steps FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to sequence enrollment" ON contact_sequence_status FOR ALL TO authenticated USING (true);

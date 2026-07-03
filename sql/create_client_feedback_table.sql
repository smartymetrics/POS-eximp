-- ============================================================
-- EXIMP & CLOVES INFRASTRUCTURE LIMITED
-- Client & Lead Feedback System Migration
-- ============================================================

CREATE TABLE IF NOT EXISTS client_feedback (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    contact_id UUID REFERENCES marketing_contacts(id) ON DELETE SET NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    user_type VARCHAR(50) DEFAULT 'other' CHECK (user_type IN ('client', 'lead', 'other')),
    feedback_type VARCHAR(50) DEFAULT 'general' CHECK (feedback_type IN ('satisfaction', 'complaint', 'suggestion', 'inquiry', 'general', 'inspection', 'allocation')),
    experience_rating INTEGER CHECK (experience_rating >= 1 AND experience_rating <= 5),
    nps_score INTEGER CHECK (nps_score >= 0 AND nps_score <= 10),
    communication_rating INTEGER CHECK (communication_rating >= 1 AND communication_rating <= 5),
    comments TEXT NOT NULL,
    property_interest_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    contact_consent BOOLEAN DEFAULT false,
    attachment_urls TEXT[] DEFAULT '{}', -- Column to store paths for uploaded screenshots/documents
    status VARCHAR(50) DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'contacted', 'resolved')),
    admin_notes TEXT,
    reviewed_by UUID REFERENCES admins(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE client_feedback ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts (public submission from website)
DROP POLICY IF EXISTS "Allow public feedback inserts" ON client_feedback;
CREATE POLICY "Allow public feedback inserts" ON client_feedback 
    FOR INSERT 
    TO public 
    WITH CHECK (true);

-- Restrict full access to authenticated admins
DROP POLICY IF EXISTS "Admins have full access to client_feedback" ON client_feedback;
CREATE POLICY "Admins have full access to client_feedback" ON client_feedback 
    FOR ALL 
    TO authenticated 
    USING (true);

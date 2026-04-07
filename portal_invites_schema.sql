-- ============================================================
-- EXIMP & CLOVES INFRASTRUCTURE LIMITED
-- Secure Portal Invitation System (PRD v1)
-- ============================================================

CREATE TABLE IF NOT EXISTS portal_invites (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('staff', 'company', 'individual')),
    token UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    is_used BOOLEAN DEFAULT false,
    invited_by UUID, -- Can be linked to admins(id) if needed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days')
);

-- RLS
ALTER TABLE portal_invites ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins have full access to portal_invites" ON portal_invites FOR ALL TO authenticated USING (true);

-- ─── BIO DATA SYSTEM MIGRATION ──────────────────────────────────────────────
-- Run this in Supabase SQL Editor

-- 1. Bio Data Settings (HR toggle on/off, general link token)
CREATE TABLE IF NOT EXISTS biodata_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    is_collecting BOOLEAN NOT NULL DEFAULT true,
    general_link_token TEXT UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex'),
    form_message TEXT DEFAULT 'Please complete your employee bio data form accurately. All information is required for official HR records.',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO biodata_settings (is_collecting) VALUES (true) ON CONFLICT DO NOTHING;

-- 2. Bio Data Invites (email-based)
CREATE TABLE IF NOT EXISTS biodata_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(32), 'hex'),
    staff_id UUID REFERENCES admins(id) ON DELETE SET NULL,
    invited_by UUID REFERENCES admins(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'approved', 'rejected')),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    used_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_biodata_invites_email ON biodata_invites(email);
CREATE INDEX IF NOT EXISTS idx_biodata_invites_token ON biodata_invites(token);

-- 3. Bio Data Submissions
CREATE TABLE IF NOT EXISTS biodata_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invite_id UUID REFERENCES biodata_invites(id) ON DELETE SET NULL,
    staff_id UUID REFERENCES admins(id) ON DELETE SET NULL,
    email TEXT NOT NULL,

    -- Personal
    surname TEXT,
    other_names TEXT,
    marital_status TEXT,
    gender TEXT,
    job_title TEXT,
    date_of_birth TEXT,
    joining_date TEXT,
    present_home_address TEXT,
    mobile_phone TEXT,
    house_phone TEXT,
    next_of_kin_name TEXT,
    next_of_kin_phone TEXT,

    -- File uploads (Supabase storage paths in hr_documents bucket)
    passport_photo_path TEXT,
    passport_photo_url TEXT,

    -- Drawn signature (base64 PNG stored as Supabase storage path)
    signature_path TEXT,
    signature_url TEXT,

    -- Authenticity metadata (all compulsory)
    ip_address TEXT,
    device_type TEXT,
    user_agent TEXT,
    coordinates_lat DOUBLE PRECISION,
    coordinates_lng DOUBLE PRECISION,
    coordinates_accuracy DOUBLE PRECISION,
    submitted_at TIMESTAMPTZ,

    -- Review
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by UUID REFERENCES admins(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_biodata_submissions_email ON biodata_submissions(email);
CREATE INDEX IF NOT EXISTS idx_biodata_submissions_status ON biodata_submissions(status);
CREATE INDEX IF NOT EXISTS idx_biodata_submissions_staff_id ON biodata_submissions(staff_id);

-- 4. Enable RLS but allow service role full access
ALTER TABLE biodata_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE biodata_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE biodata_submissions ENABLE ROW LEVEL SECURITY;

-- Service role bypass (backend uses service role key)
CREATE POLICY "service_role_all_settings" ON biodata_settings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_invites" ON biodata_invites FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_submissions" ON biodata_submissions FOR ALL TO service_role USING (true) WITH CHECK (true);
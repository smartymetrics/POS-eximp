-- ── GUARANTOR FORM SYSTEM SCHEMA ───────────────────────────────────────────

-- 1. Guarantor Submissions
CREATE TABLE IF NOT EXISTS guarantor_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_name TEXT NOT NULL,
    employee_email TEXT NOT NULL,
    position TEXT,
    staff_id TEXT,
    date_of_employment DATE,
    employee_phone TEXT,
    employee_address TEXT,
    employee_signature_url TEXT,
    
    -- Global status
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    
    -- Granular Section Statuses
    section_a_status TEXT DEFAULT 'pending', -- Employee details
    section_a_reason TEXT,
    section_b_status TEXT DEFAULT 'pending', -- Guarantor 1
    section_b_reason TEXT,
    section_c_status TEXT DEFAULT 'pending', -- Guarantor 2
    section_c_reason TEXT,
    
    submitted_at TIMESTAMPTZ DEFAULT now(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES admins(id)
);

-- 2. Guarantors (Slots 1 and 2 per submission)
CREATE TABLE IF NOT EXISTS guarantors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID REFERENCES guarantor_submissions(id) ON DELETE CASCADE,
    slot_number INTEGER NOT NULL, -- 1 or 2
    
    full_name TEXT,
    relationship TEXT,
    address TEXT,
    occupation TEXT,
    employer_name TEXT,
    position_held TEXT,
    years_at_job TEXT,
    phone TEXT,
    email TEXT,
    id_type TEXT,
    id_number TEXT,
    passport_photo_url TEXT,
    id_document_url TEXT,
    signature_url TEXT,
    
    -- Witness Details (Section D)
    witness_name TEXT,
    witness_occupation TEXT,
    witness_phone TEXT,
    witness_address TEXT,
    witness_date DATE,
    
    UNIQUE(submission_id, slot_number)
);

-- 3. Guarantor Invitations (Private Tokens)
CREATE TABLE IF NOT EXISTS guarantor_invites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, used, expired
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    created_by UUID REFERENCES admins(id)
);

-- 4. Global Settings & General Link
CREATE TABLE IF NOT EXISTS guarantor_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_collecting BOOLEAN DEFAULT TRUE,
    general_link_token TEXT DEFAULT 'general',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Seed default settings
INSERT INTO guarantor_settings (general_link_token) 
VALUES ('general')
ON CONFLICT DO NOTHING;

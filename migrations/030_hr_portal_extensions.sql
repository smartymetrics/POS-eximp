-- Missing Tables for HRM Portal (Hubs 1-9 Integration)

-- 1. Notifications System
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- letter_issued, task_assigned, recognition, etc.
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Succession Planning
CREATE TABLE IF NOT EXISTS succession_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    critical_role TEXT NOT NULL,
    successor_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    readiness TEXT NOT NULL, -- Ready Now, 6-12 months, etc.
    development_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. HR Tax Configuration (Global)
CREATE TABLE IF NOT EXISTS hr_tax_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paye_enabled BOOLEAN DEFAULT TRUE,
    pension_employee_rate NUMERIC DEFAULT 8,
    pension_employer_rate NUMERIC DEFAULT 10,
    nhf_rate NUMERIC DEFAULT 2.5,
    wht_default_rate NUMERIC DEFAULT 5,
    wht_contractor_rate NUMERIC DEFAULT 10,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed one tax config record if empty
INSERT INTO hr_tax_config (id) 
SELECT '00000000-0000-0000-0000-000000000001'
WHERE NOT EXISTS (SELECT 1 FROM hr_tax_config);

-- 4. Remote Work Tracking
CREATE TABLE IF NOT EXISTS remote_work_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    location TEXT,
    reason TEXT,
    status TEXT DEFAULT 'pending', -- pending | approved | rejected
    approved_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Exit Interviews
CREATE TABLE IF NOT EXISTS exit_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    exit_date DATE NOT NULL,
    reason TEXT,
    overall_satisfaction INTEGER CHECK (overall_satisfaction BETWEEN 1 AND 5),
    highlights TEXT,
    concerns TEXT,
    would_recommend BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. General HR Requests (Equipment, Access, etc.)
CREATE TABLE IF NOT EXISTS hr_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    request_type TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'Normal',
    status TEXT DEFAULT 'pending', -- pending | approved | rejected | completed
    resolved_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Policy Library
CREATE TABLE IF NOT EXISTS hr_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT,
    document_url TEXT,
    effective_date DATE,
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure other standard tables from hr_new_tables.sql exist
-- Recognition (Kudos Wall)
CREATE TABLE IF NOT EXISTS recognition (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id UUID REFERENCES admins(id),
    giver_id UUID REFERENCES admins(id),
    message TEXT NOT NULL,
    badge_type TEXT DEFAULT 'Kudos',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HR Letters
CREATE TABLE IF NOT EXISTS hr_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id),
    letter_type TEXT NOT NULL,
    content TEXT NOT NULL,
    date_issued DATE NOT NULL,
    issued_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Grievances
CREATE TABLE IF NOT EXISTS grievances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    is_anonymous BOOLEAN DEFAULT TRUE,
    filed_by UUID REFERENCES admins(id),
    against_staff_id UUID REFERENCES admins(id),
    status TEXT DEFAULT 'open', -- open | under_review | resolved | dismissed
    resolved_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

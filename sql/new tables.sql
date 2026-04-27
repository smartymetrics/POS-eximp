-- 1. ROBUST NOTIFICATIONS FIX
-- Create the table if it doesn't exist at all
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT DEFAULT 'general',
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- If the table exists but uses 'staff_id', add 'admin_id' as an alias or rename it
DO $$ 
BEGIN 
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='notifications' AND column_name='staff_id') THEN
        ALTER TABLE notifications RENAME COLUMN staff_id TO admin_id;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='notifications' AND column_name='type') THEN
        ALTER TABLE notifications RENAME COLUMN type TO notification_type;
    END IF;
END $$;

-- 2. ENSURE ALL HRM TABLES ARE PRESENT
CREATE TABLE IF NOT EXISTS hr_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    request_type TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'Normal',
    status TEXT DEFAULT 'pending',
    resolved_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_requisitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    department TEXT,
    employment_type TEXT,
    status TEXT DEFAULT 'Pending Approval',
    is_internal BOOLEAN DEFAULT FALSE,
    description TEXT,
    requirements TEXT,
    responsibilities TEXT,
    salary_range TEXT,
    location TEXT,
    headcount INT DEFAULT 1,
    justification TEXT,
    closing_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- If the table already exists, add any missing columns safely
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS is_internal BOOLEAN DEFAULT FALSE;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS requirements TEXT;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS responsibilities TEXT;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS headcount INT DEFAULT 1;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS justification TEXT;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS closing_date DATE;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS salary_range TEXT;
ALTER TABLE job_requisitions ADD COLUMN IF NOT EXISTS description TEXT;

-- Ensure interviews table exists
CREATE TABLE IF NOT EXISTS job_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES job_applications(id) ON DELETE CASCADE,
    interviewer_id UUID,
    scheduled_at TIMESTAMPTZ NOT NULL,
    interview_type TEXT DEFAULT 'Technical',
    location TEXT,
    notes TEXT,
    outcome TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure interviewer_id doesn't have a strict FK that blocks admin IDs if it was previously set to staff_profiles
ALTER TABLE job_interviews DROP CONSTRAINT IF EXISTS job_interviews_interviewer_id_fkey;
ALTER TABLE job_interviews ADD COLUMN IF NOT EXISTS interview_type TEXT DEFAULT 'Technical';
ALTER TABLE job_interviews ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE job_interviews ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE job_interviews ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'scheduled';
ALTER TABLE job_interviews ADD COLUMN IF NOT EXISTS outcome TEXT;


CREATE TABLE IF NOT EXISTS job_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES job_requisitions(id) ON DELETE SET NULL,
    candidate_name TEXT NOT NULL,
    candidate_email TEXT NOT NULL,
    candidate_phone TEXT,
    resume_url TEXT,
    cover_letter TEXT,
    status TEXT DEFAULT 'Applied',
    offered_salary TEXT,
    start_date DATE,
    notes TEXT,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Safely add columns if the table already exists
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS candidate_phone TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS resume_url TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS cover_letter TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS offered_salary TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS start_date DATE;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

CREATE TABLE IF NOT EXISTS announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    priority TEXT DEFAULT 'Normal',
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS grievances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    filed_by UUID REFERENCES admins(id),
    status TEXT DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hr_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID REFERENCES admins(id),
    letter_type TEXT NOT NULL,
    content TEXT NOT NULL,
    date_issued DATE NOT NULL,
    issued_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

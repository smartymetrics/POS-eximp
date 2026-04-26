-- Migration for HR Recruitment & ATS System

CREATE TABLE IF NOT EXISTS job_requisitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    department TEXT NOT NULL,
    employment_type TEXT NOT NULL, -- Full-time, Part-time, Contract
    location TEXT,
    status TEXT DEFAULT 'Open', -- Open, Draft, Closed, On Hold
    description TEXT,
    requirements TEXT,
    salary_range TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES job_requisitions(id) ON DELETE CASCADE,
    candidate_name TEXT NOT NULL,
    candidate_email TEXT NOT NULL,
    candidate_phone TEXT,
    resume_url TEXT,
    cover_letter TEXT,
    status TEXT DEFAULT 'Applied', -- Applied, Screening, Interview, Offered, Hired, Rejected
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS job_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES job_applications(id) ON DELETE CASCADE,
    interviewer_id UUID REFERENCES staff_profiles(id) ON DELETE SET NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status TEXT DEFAULT 'Scheduled', -- Scheduled, Completed, Cancelled
    feedback TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

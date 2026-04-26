-- Migration for HR Engagement & Culture Hub (Surveys)

CREATE TABLE IF NOT EXISTS engagement_surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    questions JSONB NOT NULL, -- Array of questions
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survey_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id UUID REFERENCES engagement_surveys(id) ON DELETE CASCADE,
    staff_id UUID REFERENCES admins(id) ON DELETE SET NULL, -- Optional, for anonymous tracking
    is_anonymous BOOLEAN DEFAULT TRUE,
    answers JSONB NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

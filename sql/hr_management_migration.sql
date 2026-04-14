-- HR Management Migration Script

-- 1. Extend ADMINS table
ALTER TABLE admins ADD COLUMN IF NOT EXISTS primary_role VARCHAR(50);
ALTER TABLE admins ADD COLUMN IF NOT EXISTS department VARCHAR(100);
ALTER TABLE admins ADD COLUMN IF NOT EXISTS line_manager_id UUID REFERENCES admins(id);

-- Relax the role constraint (handle potential existing constraint names)
DO $$ 
BEGIN 
    ALTER TABLE admins DROP CONSTRAINT IF EXISTS admins_role_check;
EXCEPTION 
    WHEN others THEN NULL; 
END $$;

-- Update the check constraint to allow more roles
ALTER TABLE admins ADD CONSTRAINT admins_role_check 
CHECK (role IS NOT NULL); -- We'll handle logical role checking in backend/frontend

-- 2. Staff Profiles (Additional HR info not in admins)
CREATE TABLE IF NOT EXISTS staff_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    staff_type VARCHAR(50) DEFAULT 'full', -- full, contractor, onsite
    job_title VARCHAR(255),
    date_joined DATE,
    phone_number VARCHAR(50),
    emergency_contact VARCHAR(255),
    address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Staff Goals (KPI Tracking)
CREATE TABLE IF NOT EXISTS staff_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    kpi_name VARCHAR(255) NOT NULL,
    target_value NUMERIC DEFAULT 0,
    actual_value NUMERIC DEFAULT 0,
    unit VARCHAR(50),
    weight NUMERIC DEFAULT 1, -- For scoring (total weights should equal 100 or 1.0)
    month DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Performance Reviews (Qualitative scoring)
CREATE TABLE IF NOT EXISTS performance_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    reviewer_id UUID REFERENCES admins(id),
    review_period DATE NOT NULL,
    quality_score NUMERIC DEFAULT 0, -- 0-100 (weighted 20%)
    teamwork_score NUMERIC DEFAULT 0, -- 1-5 (part of manager review 40%)
    leadership_score NUMERIC DEFAULT 0, -- 1-5 (part of manager review 40%)
    attitude_score NUMERIC DEFAULT 0, -- 1-5 (part of manager review 40%)
    comments TEXT,
    status VARCHAR(50) DEFAULT 'draft', -- draft, submitted, final
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Leave Requests
CREATE TABLE IF NOT EXISTS leave_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    leave_type VARCHAR(50) NOT NULL, -- Annual, Sick, Study
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_count INTEGER NOT NULL,
    reason TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected
    approver_id UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Disciplinary Records (Mismanagement)
CREATE TABLE IF NOT EXISTS disciplinary_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    incident_type VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL, -- Minor, Moderate, Serious, Critical
    incident_date DATE NOT NULL,
    notes TEXT,
    logged_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS (Optional - following repo patterns)
ALTER TABLE staff_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE leave_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE disciplinary_records ENABLE ROW LEVEL SECURITY;

-- HR Management Phase 2: Detailed Profiles & Documents

-- 1. Extend Staff Profiles with Personnel Identity fields
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS dob DATE;
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS gender VARCHAR(20);
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS marital_status VARCHAR(20);
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS nationality VARCHAR(100);
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100);
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS account_number VARCHAR(50);
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS account_name VARCHAR(255);
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS cv_url TEXT;

-- 2. Staff Documents (Auxiliary files)
CREATE TABLE IF NOT EXISTS staff_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    doc_type VARCHAR(100) NOT NULL, -- CV, Contract, ID, Passport, Certificate
    title VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Staff Qualifications (Education & Skills)
CREATE TABLE IF NOT EXISTS staff_qualifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- Education, Certification, Skill
    title VARCHAR(255) NOT NULL,
    institution VARCHAR(255),
    year INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE staff_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff_qualifications ENABLE ROW LEVEL SECURITY;

-- Basic RLS Policies (Staff can view own, HR can do everything)
-- Note: Assuming authenticated users can read their own if it matches auth.uid()
-- For simplicity in this env, we ensure HR and Admin roles have full access.

DO $$ 
BEGIN
    DROP POLICY IF EXISTS "Staff can view own documents" ON staff_documents;
    CREATE POLICY "Staff can view own documents" ON staff_documents
    FOR SELECT TO authenticated
    USING (staff_id = (select id from admins where email = auth.jwt() ->> 'email' LIMIT 1));

    DROP POLICY IF EXISTS "HR can manage all documents" ON staff_documents;
    CREATE POLICY "HR can manage all documents" ON staff_documents
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM admins WHERE email = auth.jwt() ->> 'email' AND (role = 'admin' OR primary_role = 'hr')));
END $$;

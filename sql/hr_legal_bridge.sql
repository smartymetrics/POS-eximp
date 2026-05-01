-- ==========================================
-- EXTRAORDINARY LEGAL STUDIO: DATABASE BRIDGE
-- ==========================================

-- 1. Legal Matters (Generic pool for Staff, Land, Construction)
CREATE TABLE IF NOT EXISTS legal_matters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'General', -- 'Staff', 'Land', 'Construction', 'External'
    status TEXT NOT NULL DEFAULT 'Draft', -- 'Draft', 'Internal Review', 'Pending Signature', 'Executed', 'Archive'
    drafter_id UUID REFERENCES public.admins(id),
    staff_id UUID REFERENCES public.admins(id), -- Changed to reference admins(id) for consistency
    external_party_name TEXT, -- For Land/Construction
    external_party_email TEXT,
    priority TEXT DEFAULT 'Normal', -- 'Low', 'Normal', 'Critical'
    hr_memo TEXT, -- Internal notes from HR to Legal
    legal_memo TEXT, -- Internal response/status from Legal to HR
    content_html TEXT, -- High-fidelity GrapesJS HTML
    content_css TEXT,  -- High-fidelity GrapesJS CSS
    meta_data JSONB DEFAULT '{}', -- Variable data (Plot size, salary, etc.)
    executed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Legal Matter Collaborators (Permission Model)
CREATE TABLE IF NOT EXISTS legal_matter_collaborators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    matter_id UUID REFERENCES legal_matters(id) ON DELETE CASCADE,
    admin_id UUID REFERENCES public.admins(id),
    permission_level TEXT NOT NULL DEFAULT 'View', -- 'View', 'Edit', 'Full'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. Legal Clause Library (Collaborative Assets)
CREATE TABLE IF NOT EXISTS legal_clause_library (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    clause_category TEXT DEFAULT 'General', -- 'NDA', 'Termination', 'Liability', 'Real Estate'
    content_html TEXT NOT NULL,
    created_by UUID REFERENCES public.admins(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 4. Legal Matter Signatories (Tracking & Execution)
CREATE TABLE IF NOT EXISTS legal_matter_signatories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    matter_id UUID REFERENCES legal_matters(id) ON DELETE CASCADE,
    party_name TEXT NOT NULL,
    party_email TEXT NOT NULL,
    party_role TEXT, -- 'Employee', 'Witness', 'Director', 'Lessor'
    signed_status BOOLEAN DEFAULT FALSE,
    signed_at TIMESTAMP WITH TIME ZONE,
    signature_svg TEXT,
    ip_address TEXT,
    user_agent TEXT
);

-- 5. Forensic History (Detailed Audit Trail)
CREATE TABLE IF NOT EXISTS legal_matter_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    matter_id UUID REFERENCES legal_matters(id) ON DELETE CASCADE,
    action TEXT NOT NULL, -- 'Draft Created', 'Edit', 'Sent for Signing', 'Signed', 'Permission Granted'
    performed_by UUID REFERENCES public.admins(id),
    performed_by_name TEXT, -- Performer name for audit readability
    description TEXT,
    snapshot_html TEXT, -- Save snapshots of major versions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 6. Legal Attachments
CREATE TABLE IF NOT EXISTS legal_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    matter_id UUID REFERENCES legal_matters(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_by UUID REFERENCES public.admins(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 7. Add Archival and Manual Upload Field to Staff Profiles
ALTER TABLE public.staff_profiles ADD COLUMN IF NOT EXISTS archived_legal_docs JSONB DEFAULT '[]';

-- 8. Ensure Legal Matters has communication columns (for existing tables)
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'Normal';
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS hr_memo TEXT;
ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS legal_memo TEXT;

-- 9. Fix Staff ID Foreign Key (Mismatch fix)
ALTER TABLE legal_matters DROP CONSTRAINT IF EXISTS legal_matters_staff_id_fkey;
ALTER TABLE legal_matters ADD CONSTRAINT legal_matters_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.admins(id);

-- ==========================================
-- PRE-LOAD GOLD STANDARD CLAUSES
-- ==========================================

INSERT INTO legal_clause_library (title, clause_category, content_html) VALUES
('Confidentiality Obligations', 'NDA', '<p>The Party agrees to keep all proprietary information, trade secrets, and internal operations of Eximp & Cloves Infrastructure Limited strictly confidential. This obligation survives termination of this agreement for a period of five (5) years.</p>'),
('Termination for Convenience', 'General', '<p>Either party may terminate this agreement by providing thirty (30) days written notice to the other party. Upon termination, all outstanding obligations shall be settled within seven (7) business days.</p>'),
('Governing Law (Nigeria)', 'General', '<p>This agreement shall be governed by and construed in accordance with the Laws of the Federal Republic of Nigeria. Any disputes arising shall be settled in the competent courts of Lagos State.</p>'),
('Force Majeure', 'General', '<p>Neither party shall be liable for any failure to perform its obligations where such failure results from any cause beyond the reasonable control of such party, including acts of God, war, riot, or pandemic.</p>'),
('NDPR Data Compliance', 'Compliance', '<p>In accordance with the Nigeria Data Protection Regulation (NDPR), all personal data processed during this engagement will be stored securely and only used for the specified legal purpose.</p>');

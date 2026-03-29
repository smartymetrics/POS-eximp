-- PRD 5: Contract of Sale & Digital Signing Portal Tables

-- 1. CONTRACT SIGNING SESSIONS
CREATE TABLE IF NOT EXISTS contract_signing_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'partial', 'completed', 'expired')),
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. WITNESS SIGNATURES
CREATE TABLE IF NOT EXISTS witness_signatures (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES contract_signing_sessions(id),
    witness_number INTEGER NOT NULL CHECK (witness_number IN (1, 2)),
    full_name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    occupation VARCHAR(100) NOT NULL,
    witness_email VARCHAR(255) NOT NULL,
    signature_base64 TEXT NOT NULL,
    signature_method VARCHAR(20) DEFAULT 'drawn' CHECK (signature_method IN ('drawn', 'uploaded')),
    ip_address VARCHAR(50),
    user_agent TEXT,
    signed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, witness_number)
);

-- 3. COMPANY SIGNATURES (Internal Assets)
CREATE TABLE IF NOT EXISTS company_signatures (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    role VARCHAR(50) NOT NULL CHECK (role IN ('director', 'secretary')),
    full_name VARCHAR(255) NOT NULL,
    signature_base64 TEXT NOT NULL,
    uploaded_by UUID REFERENCES admins(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. CONTRACT DOCUMENTS (History)
CREATE TABLE IF NOT EXISTS contract_documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    session_id UUID REFERENCES contract_signing_sessions(id),
    document_type VARCHAR(50) DEFAULT 'draft' CHECK (document_type IN ('draft', 'executed')),
    generated_by UUID REFERENCES admins(id),
    emailed_to VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS (Internal tables)
ALTER TABLE contract_signing_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE witness_signatures ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_signatures ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_documents ENABLE ROW LEVEL SECURITY;

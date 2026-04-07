-- ============================================================
-- EXIMP & CLOVES INFRASTRUCTURE LIMITED
-- Unified Payout, Vendor & Asset Management (PRD v3)
-- ============================================================

-- VENDORS & PAYEES
CREATE TABLE IF NOT EXISTS vendors (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    type VARCHAR(50) NOT NULL CHECK (type IN ('company', 'individual', 'staff')),
    name VARCHAR(255) NOT NULL,
    rc_number VARCHAR(100), -- Optional for individuals/staff
    tin VARCHAR(100), -- Tax Identification Number
    email VARCHAR(255),
    phone VARCHAR(50),
    
    -- Bank Details
    bank_name VARCHAR(255),
    account_number VARCHAR(50),
    account_name VARCHAR(255),
    
    -- Identity Check
    id_document_url TEXT, -- NIN, Driver's License, or CAC
    
    -- Staff Linkage
    admin_id UUID REFERENCES admins(id), -- Only populated if type='staff'
    
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- EXPENDITURE & PROCUREMENT REQUESTS
CREATE TABLE IF NOT EXISTS expenditure_requests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    requester_id UUID REFERENCES admins(id), -- Staff who initiated the request
    vendor_id UUID REFERENCES vendors(id), -- The intended recipient
    
    amount_gross DECIMAL(15,2) NOT NULL,
    payout_method VARCHAR(50) CHECK (payout_method IN ('direct_pay', 'reimbursement')),
    
    -- WHT (Withholding Tax 2025)
    is_wht_applicable BOOLEAN DEFAULT true,
    wht_rate DECIMAL(5,2) DEFAULT 0,
    wht_amount DECIMAL(15,2) DEFAULT 0,
    wht_exemption_reason TEXT,
    
    net_payout_amount DECIMAL(15,2) NOT NULL, -- Gross minus WHT
    
    -- Attachments
    receipt_url TEXT, -- For staff reimbursements
    proforma_url TEXT, -- For vendor procurement quotes
    
    status VARCHAR(50) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'awaiting_vendor_data', 'approved', 'paid', 'rejected')),
    
    reviewed_by UUID REFERENCES admins(id),
    reviewed_at TIMESTAMPTZ,
    payout_reference VARCHAR(255), -- Bank Transfer Ref
    paid_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- COMPANY ASSETS
CREATE TABLE IF NOT EXISTS company_assets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    asset_id VARCHAR(100) UNIQUE, -- e.g. EC-LAPTOP-001
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- Laptop, Phone, Tool, Vehicle
    serial_number VARCHAR(255),
    purchase_cost DECIMAL(15,2),
    purchase_date DATE,
    
    -- Link to Procurement
    procurement_id UUID REFERENCES expenditure_requests(id),
    
    assigned_to UUID REFERENCES admins(id),
    current_status VARCHAR(50) DEFAULT 'assigned' 
        CHECK (current_status IN ('assigned', 'spare', 'repair', 'lost', 'retired')),
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenditure_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins have full access to vendors" ON vendors FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to expenditure_requests" ON expenditure_requests FOR ALL TO authenticated USING (true);
CREATE POLICY "Admins have full access to company_assets" ON company_assets FOR ALL TO authenticated USING (true);

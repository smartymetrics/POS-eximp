-- Migration: Invoicing & Commission Revamp Schema Additions

-- 1. Alter invoices table
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS land_cost DECIMAL(15, 2);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS allocation_fee DECIMAL(15, 2);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS documentation_fee DECIMAL(15, 2);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS vat_amount DECIMAL(15, 2);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS discount_code VARCHAR(100);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(15, 2);

-- 2. Alter property_subscriptions table
ALTER TABLE property_subscriptions ADD COLUMN IF NOT EXISTS discount_code VARCHAR(100);
ALTER TABLE property_subscriptions ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(15, 2);

-- 3. Alter marketing_contacts table
ALTER TABLE marketing_contacts ADD COLUMN IF NOT EXISTS dob DATE;

-- 4. Create discount_codes table
CREATE TABLE IF NOT EXISTS discount_codes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    discount_type VARCHAR(20) DEFAULT 'percentage' CHECK (discount_type IN ('percentage', 'flat')),
    discount_value DECIMAL(15,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    max_uses INTEGER DEFAULT 1,
    uses_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES admins(id)
);

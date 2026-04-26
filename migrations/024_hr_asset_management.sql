-- Migration to standardize the company_assets table for HR Asset Management

CREATE TABLE IF NOT EXISTS company_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_name TEXT NOT NULL,
    asset_type TEXT,
    serial_number TEXT,
    status TEXT DEFAULT 'Available', -- Available, Assigned, Maintenance, Retired
    assigned_to UUID REFERENCES staff_profiles(id) ON DELETE SET NULL,
    payout_request_id UUID REFERENCES expenditure_requests(id) ON DELETE SET NULL, -- Link to inventory/payouts
    purchase_date DATE,
    purchase_cost NUMERIC(15,2),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure RLS is enabled and policies are set if necessary
-- Note: As this is an internal HR tool, RLS policies depend on your global setup.

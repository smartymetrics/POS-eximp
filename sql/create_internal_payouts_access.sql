CREATE TABLE IF NOT EXISTS internal_payouts_access (admin_id UUID PRIMARY KEY REFERENCES admins(id) ON DELETE CASCADE, granted_by UUID REFERENCES admins(id), granted_at TIMESTAMPTZ DEFAULT NOW());

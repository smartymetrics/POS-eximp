-- Migration: create kyc_links table to store per-rep KYC link tokens
CREATE TABLE IF NOT EXISTS kyc_links (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    rep_id UUID NOT NULL REFERENCES admins(id),
    token VARCHAR(128) UNIQUE NOT NULL,
    label VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ DEFAULT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_kyc_links_rep_id ON kyc_links(rep_id);

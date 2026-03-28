-- Migration: Add voiding fields to commission_earnings
ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS is_voided BOOLEAN DEFAULT false;

ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ;

ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS void_reason TEXT;

ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS voided_by UUID REFERENCES admins(id);

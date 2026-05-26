-- Migration: add address column to clients table
-- This supports the KYC form address field which was missing from the schema
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS address TEXT;

-- Migration: Add acknowledgement field to witness_signatures table
-- Date: 2026-03-29
-- Description: Adds acknowledgement boolean field to track witness confirmation of reading and understanding the contract

ALTER TABLE witness_signatures ADD COLUMN IF NOT EXISTS acknowledgement BOOLEAN DEFAULT false;

-- Add additional legal fields for comprehensive witness documentation
ALTER TABLE witness_signatures ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
ALTER TABLE witness_signatures ADD COLUMN IF NOT EXISTS relationship_to_parties TEXT; -- e.g., 'independent witness', 'family member', etc.

-- Update existing records to true for backwards compatibility (assuming they were acknowledged at the time)
-- This is optional and depends on business requirements
-- UPDATE witness_signatures SET acknowledgement = true WHERE acknowledgement IS NULL;
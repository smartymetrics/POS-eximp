-- Database Migration: Additive preview_text_b column for Campaign Variant B A/B tests.
-- Execute this script in your Supabase SQL Editor.

ALTER TABLE email_campaigns 
ADD COLUMN IF NOT EXISTS preview_text_b VARCHAR(500);

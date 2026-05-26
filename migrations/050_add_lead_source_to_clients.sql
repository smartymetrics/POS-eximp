-- Migration: add lead_source column to clients
-- Run with your usual migration runner (psql / supabase SQL editor)
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS lead_source VARCHAR(100);

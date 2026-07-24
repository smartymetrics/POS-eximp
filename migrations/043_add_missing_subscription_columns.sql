-- Migration 043: Add missing columns to property_subscriptions
-- Fixes PGRST204: 'purchase_for' and other fields in ALLOWED_SUB_COLUMNS
-- were never added to property_subscriptions. Using IF NOT EXISTS to be safe.

ALTER TABLE property_subscriptions
    ADD COLUMN IF NOT EXISTS purchase_for        VARCHAR(100),
    ADD COLUMN IF NOT EXISTS purchase_purpose    TEXT,
    ADD COLUMN IF NOT EXISTS ownership_type      VARCHAR(50),
    ADD COLUMN IF NOT EXISTS quantity            INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS total_amount        NUMERIC(15, 2),
    ADD COLUMN IF NOT EXISTS city                VARCHAR(100),
    ADD COLUMN IF NOT EXISTS state               VARCHAR(100),
    ADD COLUMN IF NOT EXISTS phone               VARCHAR(30),
    ADD COLUMN IF NOT EXISTS sales_rep_name      VARCHAR(255),
    ADD COLUMN IF NOT EXISTS utm_source          VARCHAR(100),
    ADD COLUMN IF NOT EXISTS utm_medium          VARCHAR(100),
    ADD COLUMN IF NOT EXISTS utm_campaign        VARCHAR(255),
    ADD COLUMN IF NOT EXISTS utm_content         VARCHAR(255),
    ADD COLUMN IF NOT EXISTS utm_term            VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ip_address          VARCHAR(45),
    ADD COLUMN IF NOT EXISTS user_agent          TEXT,
    ADD COLUMN IF NOT EXISTS consent_given       BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS consented_at        TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS co_owner_address    TEXT,
    ADD COLUMN IF NOT EXISTS co_owner_occupation VARCHAR(255),
    ADD COLUMN IF NOT EXISTS co_owner_phone      VARCHAR(30);

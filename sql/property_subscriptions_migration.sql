-- Migration to create the Property Subscription table
-- This table stores more detailed data than a standard lead, including KYC docs and signatures.

CREATE TABLE IF NOT EXISTS property_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Meta Info
    created_at TIMESTAMPTZ DEFAULT now(),
    sales_rep_id UUID REFERENCES sales_reps(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, processed, cancelled
    
    -- Bio-data
    title VARCHAR(20),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    gender VARCHAR(20),
    date_of_birth DATE,
    residential_address TEXT,
    email VARCHAR(255) NOT NULL,
    whatsapp_phone VARCHAR(50),
    marital_status VARCHAR(50),
    occupation TEXT, -- Searchable job
    nationality VARCHAR(100) DEFAULT 'Nigerian',
    
    -- KYC Documents (URLs to Supabase Storage)
    passport_photo_url TEXT,
    nin_id_number VARCHAR(100),
    nin_document_url TEXT,
    international_passport_url TEXT,
    
    -- Property Details
    property_name VARCHAR(255) NOT NULL,
    plot_size VARCHAR(100),
    ownership_type VARCHAR(100), -- sole, co-owner
    purchase_purpose VARCHAR(100), -- residential, investment, etc.
    
    -- Next of Kin
    nok_full_name VARCHAR(255),
    nok_phone VARCHAR(50),
    nok_email VARCHAR(255),
    nok_occupation VARCHAR(255),
    nok_relationship VARCHAR(100),
    nok_address TEXT,
    
    -- Co-owner (if applicable)
    co_owner_name VARCHAR(255),
    co_owner_address TEXT,
    co_owner_occupation TEXT,
    co_owner_phone VARCHAR(50),
    co_owner_email VARCHAR(255),
    
    -- Payment Information
    payment_duration VARCHAR(100),
    deposit_amount DECIMAL(15,2),
    payment_date DATE,
    payment_receipt_url TEXT,
    outstanding_payment DECIMAL(15,2),
    source_of_income TEXT,
    referral_source TEXT,
    
    -- Legal & Signature
    signature_url TEXT, -- URL to drawn signature or uploaded image
    consent_given BOOLEAN DEFAULT FALSE,
    consented_at TIMESTAMPTZ,
    
    -- Form Identification
    ip_address VARCHAR(50),
    user_agent TEXT
);

-- Add index for sales reps to track performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_rep ON property_subscriptions(sales_rep_id);

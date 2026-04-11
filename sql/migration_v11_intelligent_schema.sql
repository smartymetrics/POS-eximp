-- Recovery Migration v11: Create property_subscriptions with all required columns
CREATE TABLE IF NOT EXISTS property_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Subscriber Bio-data
    title VARCHAR(50),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    middle_name VARCHAR(255),
    gender VARCHAR(20),
    date_of_birth DATE,
    residential_address TEXT,
    email VARCHAR(255) NOT NULL,
    whatsapp_phone VARCHAR(50),
    phone VARCHAR(50),
    marital_status VARCHAR(50),
    occupation VARCHAR(255),
    nationality VARCHAR(100) DEFAULT 'Nigerian',
    city VARCHAR(255),
    state VARCHAR(255),

    -- KYC
    passport_photo_url TEXT,
    nin_id_number VARCHAR(100),
    nin_document_url TEXT,
    international_passport_url TEXT,

    -- Purchase Details
    property_name VARCHAR(255),
    plot_size VARCHAR(100),
    quantity INTEGER DEFAULT 1,
    ownership_type VARCHAR(50),
    purchase_purpose VARCHAR(100),
    total_amount DECIMAL(15,2),
    deposit_amount DECIMAL(15,2),
    payment_duration VARCHAR(100),
    payment_date DATE,
    payment_receipt_url TEXT,
    source_of_income VARCHAR(255),
    referral_source VARCHAR(255),

    -- Co-Owner (Optional)
    co_owner_name VARCHAR(255),
    co_owner_address TEXT,
    co_owner_occupation VARCHAR(255),
    co_owner_phone VARCHAR(50),
    co_owner_email VARCHAR(255),

    -- Legal & Attribution
    signature_url TEXT,
    consent_given BOOLEAN DEFAULT FALSE,
    consented_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    sales_rep_id UUID REFERENCES sales_reps(id),
    sales_rep_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',

    -- Marketing Attribution
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    utm_content VARCHAR(255),
    utm_term VARCHAR(255)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_email ON property_subscriptions(email);
CREATE INDEX IF NOT EXISTS idx_subscriptions_phone ON property_subscriptions(phone);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON property_subscriptions(status);

-- RE-ESTABLISH RELATIONSHIPS
-- This is critical for the Admin Dashboard (routers/verifications.py) to work

-- 1. Ensure the column exists first
ALTER TABLE pending_verifications 
ADD COLUMN IF NOT EXISTS subscription_id UUID;

-- 2. Link it to property_subscriptions
ALTER TABLE pending_verifications 
DROP CONSTRAINT IF EXISTS fk_pending_verifications_subscription;

ALTER TABLE pending_verifications
ADD CONSTRAINT fk_pending_verifications_subscription 
FOREIGN KEY (subscription_id) 
REFERENCES property_subscriptions(id)
ON DELETE SET NULL;

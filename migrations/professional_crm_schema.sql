-- Professional CRM Database Schema Extensions
-- Run this migration to add professional CRM features

-- Properties Table (for land & house listings)
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    property_type VARCHAR(50),  -- residential, commercial, land
    bedrooms INT,
    bathrooms INT,
    sq_feet DECIMAL(10, 2),
    price DECIMAL(15, 2),
    description TEXT,
    owner_agent_id UUID REFERENCES admins(id),
    status VARCHAR(50) DEFAULT 'available',  -- available, sold, pending
    photos JSONB DEFAULT '[]',
    virtual_tour_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Property Media (photos, videos, tours)
CREATE TABLE IF NOT EXISTS property_media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    type VARCHAR(50),  -- photo, video, tour
    url TEXT,
    description TEXT,
    "order" INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Property Interests (track which clients are interested in which properties)
CREATE TABLE IF NOT EXISTS property_interests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    interest_level VARCHAR(50),  -- high, medium, low
    inquired_at TIMESTAMP DEFAULT NOW()
);

-- Property Inquiries
CREATE TABLE IF NOT EXISTS property_inquiries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20),
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Documents (contracts, agreements, deeds)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_type VARCHAR(50),  -- contract, agreement, deed, proposal
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    title VARCHAR(255),
    file_url TEXT,
    status VARCHAR(50) DEFAULT 'draft',  -- draft, sent, signed, executed
    created_by UUID REFERENCES admins(id),
    sent_at TIMESTAMP,
    sent_to_email VARCHAR(255),
    esignature_link TEXT,
    signed_at TIMESTAMP,
    signed_by_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Campaigns (SMS, Email campaigns)
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50),  -- sms, email
    name VARCHAR(255),
    target_segment VARCHAR(100),  -- hot_leads, warm_leads, past_buyers
    message_template TEXT,
    schedule VARCHAR(50),  -- immediate, daily, weekly
    schedule_time TIME,
    created_by UUID REFERENCES admins(id),
    status VARCHAR(50) DEFAULT 'draft',  -- draft, scheduled, sent
    sent_at TIMESTAMP,
    messages_sent INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Campaign Messages (individual message records)
CREATE TABLE IF NOT EXISTS campaign_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    type VARCHAR(50),  -- sms, email
    status VARCHAR(50) DEFAULT 'sent',  -- sent, opened, clicked, converted
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    converted_at TIMESTAMP
);

-- Lead Scores (store calculated scores for tracking and sorting)
CREATE TABLE IF NOT EXISTS lead_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    score DECIMAL(5, 1),  -- 0-100
    quality VARCHAR(50),  -- HOT, WARM, LUKEWARM, COLD
    urgency VARCHAR(50),  -- IMMEDIATE, HIGH, MEDIUM, LOW
    factors JSONB,  -- Store individual scoring factors
    calculated_at TIMESTAMP DEFAULT NOW()
);

-- Create Indexes for Performance
CREATE INDEX ON properties(status);
CREATE INDEX ON properties(city);
CREATE INDEX ON properties(owner_agent_id);
CREATE INDEX ON property_interests(client_id);
CREATE INDEX ON property_interests(property_id);
CREATE INDEX ON documents(client_id);
CREATE INDEX ON documents(status);
CREATE INDEX ON campaigns(type);
CREATE INDEX ON campaigns(status);
CREATE INDEX ON campaign_messages(campaign_id);
CREATE INDEX ON campaign_messages(client_id);
CREATE INDEX ON campaign_messages(status);
CREATE INDEX ON lead_scores(client_id);
CREATE INDEX ON lead_scores(score DESC);

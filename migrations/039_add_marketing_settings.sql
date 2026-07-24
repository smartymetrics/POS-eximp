-- Create marketing_settings table for global configurations
CREATE TABLE IF NOT EXISTS marketing_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key TEXT UNIQUE NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Initialize default settings
INSERT INTO marketing_settings (key, value)
VALUES ('daily_quota', '{"enabled": true, "limit": 80, "reset_hour": 0}')
ON CONFLICT (key) DO NOTHING;

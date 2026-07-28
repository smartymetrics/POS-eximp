-- Migration 056: Newsletter subscriptions (double opt-in verification & progressive profiling)

CREATE TABLE IF NOT EXISTS blog_newsletter_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    verification_token UUID NOT NULL DEFAULT gen_random_uuid(),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',  -- pending | verified
    token_expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blog_newsletter_email ON blog_newsletter_subscriptions(email);
CREATE INDEX IF NOT EXISTS idx_blog_newsletter_token ON blog_newsletter_subscriptions(verification_token);

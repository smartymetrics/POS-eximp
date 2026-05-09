-- Create procurement_invites table for quotation invitation system
CREATE TABLE IF NOT EXISTS public.procurement_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    vendor_email VARCHAR(255) NOT NULL,
    vendor_id UUID REFERENCES public.vendors(id) ON DELETE SET NULL,
    project VARCHAR(255),
    message TEXT,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '30 days'),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired')),
    CONSTRAINT vendor_email_not_empty CHECK (vendor_email <> ''),
    CONSTRAINT valid_token CHECK (token IS NOT NULL)
);

-- Create index on token for fast lookup
CREATE INDEX idx_procurement_invites_token ON public.procurement_invites(token);

-- Create index on vendor_email for lookups
CREATE INDEX idx_procurement_invites_email ON public.procurement_invites(vendor_email);

-- Create index on status for filtering
CREATE INDEX idx_procurement_invites_status ON public.procurement_invites(status);

-- Create index on expires_at for cleanup queries
CREATE INDEX idx_procurement_invites_expires ON public.procurement_invites(expires_at);

-- Optional: Auto-update status to 'expired' when checking expiry (via trigger in app logic)
-- Alternatively, update status to expired when reading

GRANT SELECT, INSERT, UPDATE ON public.procurement_invites TO authenticated;
GRANT SELECT ON public.procurement_invites TO anon;

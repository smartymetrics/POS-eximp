-- Migration: create refund_requests table
CREATE TABLE IF NOT EXISTS public.refund_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    estate_bought TEXT NOT NULL,
    invoice_number TEXT,
    comment TEXT,
    files JSONB DEFAULT '[]'::jsonb,
    status TEXT DEFAULT 'submitted',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Optional: create index on created_at for faster admin queries
CREATE INDEX IF NOT EXISTS idx_refund_requests_created_at ON public.refund_requests (created_at DESC);

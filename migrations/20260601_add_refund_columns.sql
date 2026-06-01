-- Migration: add status_reason and email_error columns to refund_requests
ALTER TABLE public.refund_requests
  ADD COLUMN IF NOT EXISTS status_reason TEXT,
  ADD COLUMN IF NOT EXISTS email_error TEXT;

-- Consider adding an index on status for faster admin filtering
CREATE INDEX IF NOT EXISTS idx_refund_requests_status ON public.refund_requests (status);

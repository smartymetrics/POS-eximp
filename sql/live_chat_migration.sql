-- Migration for Live Support & Automated Nudge
ALTER TABLE support_tickets 
ADD COLUMN IF NOT EXISTS last_admin_response_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS followup_sent_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS admin_typing_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS client_typing_at TIMESTAMPTZ;

-- Add a comment for future reference
COMMENT ON COLUMN support_tickets.last_admin_response_at IS 'Timestamp of the last message sent by an admin';
COMMENT ON COLUMN support_tickets.followup_sent_at IS 'Timestamp when the 1-hour nudge email was last sent';

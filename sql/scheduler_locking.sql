-- Table to prevent multiple workers from running the same job simultaneously
CREATE TABLE IF NOT EXISTS scheduler_locks (
    job_key TEXT PRIMARY KEY,
    last_run_at TIMESTAMPTZ,
    locked_until TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pre-seed core job keys for safety
INSERT INTO scheduler_locks (job_key) VALUES 
('marketing_automation'),
('segment_trigger_monitor'),
('appointment_reminders'),
('support_nudges')
ON CONFLICT (job_key) DO NOTHING;

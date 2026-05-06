-- guarantor_submissions table
ALTER TABLE guarantor_submissions
  ADD COLUMN IF NOT EXISTS employee_signed_at   timestamptz,
  ADD COLUMN IF NOT EXISTS employee_ip           text,
  ADD COLUMN IF NOT EXISTS employee_device_type  text,
  ADD COLUMN IF NOT EXISTS employee_user_agent   text,
  ADD COLUMN IF NOT EXISTS employee_signed_date  text;

-- guarantors table
ALTER TABLE guarantors
  ADD COLUMN IF NOT EXISTS signed_at    timestamptz,
  ADD COLUMN IF NOT EXISTS ip_address   text,
  ADD COLUMN IF NOT EXISTS device_type  text,
  ADD COLUMN IF NOT EXISTS user_agent   text,
  ADD COLUMN IF NOT EXISTS signed_date  text;
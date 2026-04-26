-- Migration to support Nigerian Tax Engine (PAYE/Pension)

ALTER TABLE payroll_records ADD COLUMN IF NOT EXISTS pension NUMERIC(15,2) DEFAULT 0;
ALTER TABLE payroll_records ADD COLUMN IF NOT EXISTS cra NUMERIC(15,2) DEFAULT 0;

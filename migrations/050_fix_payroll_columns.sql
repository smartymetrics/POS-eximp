
-- Migration: Add missing payroll columns for advanced tax engine
-- Added by Antigravity AI

ALTER TABLE payroll_records ADD COLUMN IF NOT EXISTS nhf NUMERIC DEFAULT 0;
ALTER TABLE payroll_records ADD COLUMN IF NOT EXISTS employer_pension NUMERIC DEFAULT 0;
ALTER TABLE payroll_records ADD COLUMN IF NOT EXISTS net_pay_breakdown JSONB DEFAULT '{}'::jsonb;

-- Comment to track column purpose
COMMENT ON COLUMN payroll_records.nhf IS 'National Housing Fund contribution';
COMMENT ON COLUMN payroll_records.employer_pension IS 'Pension contribution paid by the employer';
COMMENT ON COLUMN payroll_records.net_pay_breakdown IS 'Detailed breakdown of the net pay calculation for payslip rendering';

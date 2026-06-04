-- Migration 051: NTA 2025 payroll updates
-- Removes the unused CRA column (payroll never run in production).
-- Adds payslip_sent_at for email tracking.
-- No rent relief columns: rent relief is a personal deduction the employee
-- claims on their own annual tax return (Form A with FIRS/SIRS) and is
-- not the employer's obligation to compute or store.

-- 1. Remove unused CRA column from payroll_records
--    Safe: payroll has never been run in production per developer confirmation.
ALTER TABLE payroll_records DROP COLUMN IF EXISTS cra;

-- 2. Track when payslip was emailed to the staff member
ALTER TABLE payroll_records
  ADD COLUMN IF NOT EXISTS payslip_sent_at TIMESTAMPTZ;

COMMENT ON COLUMN payroll_records.payslip_sent_at
  IS 'Timestamp of when the payslip PDF was last emailed to the staff member';
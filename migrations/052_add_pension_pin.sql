-- Migration 052: Add pension_pin to staff_profiles
-- Pension PIN (PFA registration number) is needed on payslips per PRA 2014
ALTER TABLE staff_profiles
  ADD COLUMN IF NOT EXISTS pension_pin TEXT;

COMMENT ON COLUMN staff_profiles.pension_pin
  IS 'Pension Fund Administrator (PFA) registration PIN — required on payslips per PRA 2014';
-- HR Phase 5: Attendance Records & Salary Baseline
-- This migration adds the attendance tracking table and prepares staff profiles for automated payroll.

-- 1. Add base_salary to staff_profiles for payroll automation
ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS base_salary NUMERIC(12, 2) DEFAULT 0.00;

-- 2. Create Attendance Records Table
CREATE TABLE IF NOT EXISTS attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    check_in TIMESTAMPTZ,
    check_out TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'Present', -- Present, Late, Absent, On Leave
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(staff_id, date)
);

-- Enable RLS
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DO $$
BEGIN
    -- HR/Admin can manage all attendance
    DROP POLICY IF EXISTS "HR can manage all attendance" ON attendance_records;
    CREATE POLICY "HR can manage all attendance" ON attendance_records
    FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM admins
        WHERE email = auth.jwt() ->> 'email'
        AND (role LIKE '%admin%' OR primary_role = 'hr')
    ));

    -- Staff can view their own attendance
    DROP POLICY IF EXISTS "Staff can view own attendance" ON attendance_records;
    CREATE POLICY "Staff can view own attendance" ON attendance_records
    FOR SELECT TO authenticated
    USING (staff_id = (SELECT id FROM admins WHERE email = auth.jwt() ->> 'email' LIMIT 1));
END $$;

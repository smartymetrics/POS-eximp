-- HR Phase 4: Payroll Records Table
-- This table is used by the Payroll module in the HR portal.

CREATE TABLE IF NOT EXISTS payroll_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    gross_pay NUMERIC(12, 2) DEFAULT 0.00,
    net_pay NUMERIC(12, 2) DEFAULT 0.00,
    deductions NUMERIC(12, 2) DEFAULT 0.00,
    tax NUMERIC(12, 2) DEFAULT 0.00,
    status VARCHAR(50) DEFAULT 'paid', -- paid, pending, processing
    processed_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE payroll_records ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DO $$
BEGIN
    -- HR/Admin can manage all payroll
    DROP POLICY IF EXISTS "HR can manage all payroll" ON payroll_records;
    CREATE POLICY "HR can manage all payroll" ON payroll_records
    FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM admins
        WHERE email = auth.jwt() ->> 'email'
        AND (role LIKE '%admin%' OR primary_role = 'hr')
    ));

    -- Staff can view their own payslips
    DROP POLICY IF EXISTS "Staff can view own payslips" ON payroll_records;
    CREATE POLICY "Staff can view own payslips" ON payroll_records
    FOR SELECT TO authenticated
    USING (staff_id = (SELECT id FROM admins WHERE email = auth.jwt() ->> 'email' LIMIT 1));
END $$;

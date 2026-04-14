-- HR Phase 3: Staff Tasks Table
-- This table is used by the Task Manager module in the HR portal.

CREATE TABLE IF NOT EXISTS staff_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assigned_to UUID REFERENCES admins(id) ON DELETE CASCADE,
    created_by UUID REFERENCES admins(id),
    title VARCHAR(255) NOT NULL,
    notes TEXT,
    priority VARCHAR(50) DEFAULT 'Medium', -- High, Medium, Low
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed
    due_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE staff_tasks ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DO $$
BEGIN
    -- HR/Admin can manage all tasks
    DROP POLICY IF EXISTS "HR can manage all tasks" ON staff_tasks;
    CREATE POLICY "HR can manage all tasks" ON staff_tasks
    FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM admins
        WHERE email = auth.jwt() ->> 'email'
        AND (role LIKE '%admin%' OR primary_role = 'hr')
    ));

    -- Staff can view their own tasks
    DROP POLICY IF EXISTS "Staff can view own tasks" ON staff_tasks;
    CREATE POLICY "Staff can view own tasks" ON staff_tasks
    FOR SELECT TO authenticated
    USING (assigned_to = (SELECT id FROM admins WHERE email = auth.jwt() ->> 'email' LIMIT 1));

    -- Staff can update status of their own tasks
    DROP POLICY IF EXISTS "Staff can update own task status" ON staff_tasks;
    CREATE POLICY "Staff can update own task status" ON staff_tasks
    FOR UPDATE TO authenticated
    USING (assigned_to = (SELECT id FROM admins WHERE email = auth.jwt() ->> 'email' LIMIT 1))
    WITH CHECK (assigned_to = (SELECT id FROM admins WHERE email = auth.jwt() ->> 'email' LIMIT 1));
END $$;

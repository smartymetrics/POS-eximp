-- ============================================================
-- CRM Improvement Migration
-- Covers: Sections 7a, 10a, and 1a from the spec
-- Run this FIRST before any backend/frontend changes
-- ============================================================

-- SECTION 7a: Add last_contacted_at to clients table
ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_contacted_at TIMESTAMPTZ DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_clients_last_contacted ON clients(last_contacted_at);

-- SECTION 10a: Create crm_tasks table
CREATE TABLE IF NOT EXISTS crm_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assigned_to UUID REFERENCES admins(id) ON DELETE CASCADE,   -- the rep
    assigned_by UUID REFERENCES admins(id),                     -- the manager
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,    -- the client to contact
    title VARCHAR(255) NOT NULL,
    notes TEXT,
    due_date DATE,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'dismissed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_tasks_assigned_to ON crm_tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_crm_tasks_status ON crm_tasks(status);
CREATE INDEX IF NOT EXISTS idx_crm_tasks_due_date ON crm_tasks(due_date);

-- SECTION 1a: Document the sales_manager role (no new table needed)
-- Role constraint was already dropped in rbac_migration.sql
COMMENT ON COLUMN admins.role IS 'Valid roles: super_admin, admin, operations, sales_manager, customer_support, legal, lawyer, hr_admin, sales, marketing, staff';
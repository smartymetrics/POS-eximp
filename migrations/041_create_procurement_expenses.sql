-- Migration: Create procurement_expenses table
-- Description: Separate table for estate development and procurement costs

CREATE TABLE IF NOT EXISTS procurement_expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    category TEXT NOT NULL, -- Clearing, Fencing, Survey, etc.
    amount DECIMAL(15, 2) NOT NULL DEFAULT 0,
    vendor_name TEXT,
    vendor_id UUID REFERENCES vendors(id) ON DELETE SET NULL,
    expense_date DATE DEFAULT CURRENT_DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES admins(id)
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_procurement_property ON procurement_expenses(property_id);
CREATE INDEX IF NOT EXISTS idx_procurement_category ON procurement_expenses(category);

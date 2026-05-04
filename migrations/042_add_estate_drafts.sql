-- Migration: Create estate_drafts table
-- Description: Sandbox for planning estates before they go live in the ERP

CREATE TABLE IF NOT EXISTS estate_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT,
    variations JSONB NOT NULL DEFAULT '[]', -- Array of {size_sqm: number, outright_price: number, installment_price: number, total_plots: number, acquisition_cost: number}
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES admins(id)
);

-- Ensure procurement_expenses exists first (it should from 041)
CREATE TABLE IF NOT EXISTS procurement_expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES properties(id),
    estate_draft_id UUID REFERENCES estate_drafts(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    expense_date DATE DEFAULT CURRENT_DATE,
    vendor_name TEXT,
    vendor_id UUID,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

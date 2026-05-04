-- MIGRATION: Add Procurement & Estate Development Tracking
-- This enables linking expenses to specific estates for ROI analysis.

-- 1. Add property_id to expenditure_requests
ALTER TABLE expenditure_requests 
ADD COLUMN IF NOT EXISTS property_id UUID REFERENCES properties(id);

-- 2. Add acquisition_cost and total_plots to properties (The price the company paid for the land)
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS acquisition_cost DECIMAL(15,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_plots INTEGER DEFAULT 0;

-- 3. Add project_category for better analysis (e.g. 'Clearing', 'Fencing')
ALTER TABLE expenditure_requests 
ADD COLUMN IF NOT EXISTS development_category VARCHAR(100);

-- 4. Create an index for fast lookups
CREATE INDEX IF NOT EXISTS idx_expenditure_property ON expenditure_requests(property_id);

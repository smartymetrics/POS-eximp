-- Table to store custom marketing events/occasions
CREATE TABLE IF NOT EXISTS marketing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    event_date DATE NOT NULL,
    action TEXT,
    event_type TEXT DEFAULT 'custom',
    is_recurring BOOLEAN DEFAULT FALSE,
    frequency TEXT CHECK (frequency IN ('weekly', 'monthly', 'yearly')),
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    created_by UUID REFERENCES admins(id)
);

-- Index for date-based lookups
CREATE INDEX IF NOT EXISTS idx_marketing_events_date ON marketing_events(event_date);

-- RLS (Row Level Security) - Optional but good practice
ALTER TABLE marketing_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all authenticated users full access to marketing events" 
ON marketing_events FOR ALL 
USING (auth.role() = 'authenticated');

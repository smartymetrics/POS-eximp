ALTER TABLE public.marketing_sequences 
ADD COLUMN IF NOT EXISTS trigger_segment_id UUID REFERENCES public.marketing_segments(id) ON DELETE SET NULL;

-- 2. Join table for manual / static segments
CREATE TABLE IF NOT EXISTS public.marketing_segment_contacts (
    segment_id UUID REFERENCES public.marketing_segments(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES public.marketing_contacts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (segment_id, contact_id)
);

-- RLS for join table
ALTER TABLE public.marketing_segment_contacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins have full access to segment contacts" ON public.marketing_segment_contacts FOR ALL TO authenticated USING (true);

COMMENT ON COLUMN public.marketing_sequences.trigger_event IS 'Specific event that enrolls a contact: manual, client_created, segment_entry';
COMMENT ON COLUMN public.marketing_sequences.trigger_segment_id IS 'If trigger_event is segment_entry, this segment is monitored for new members.';

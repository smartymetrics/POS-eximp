-- migration to add notification system
CREATE TABLE IF NOT EXISTS notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    admin_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'general', -- 'support', 'lead', 'invoice', 'general'
    reference_id UUID, -- ticket_id, invoice_id, etc.
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_notifications_admin_read ON notifications(admin_id, is_read);

-- Enable RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Simple policy for admins to see their own -- SIMPLE POLICIES
 CREATE POLICY "Admins see own notifications" ON notifications FOR SELECT TO authenticated USING (admin_id = auth.uid());
 CREATE POLICY "Admins update own notifications" ON notifications FOR UPDATE TO authenticated USING (admin_id = auth.uid());

-- Ensure support_tickets has the assigned_admin_id column
ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS assigned_admin_id UUID REFERENCES admins(id);

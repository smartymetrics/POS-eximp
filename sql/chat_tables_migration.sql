-- Phase 2: Group Chat Technical Spec
-- Create the chat rooms, participants, and messages tables

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. chat_rooms table
CREATE TABLE chat_rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    created_by_admin_id UUID NOT NULL REFERENCES admins(id),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticket_id) -- one room per ticket
);

-- 2. chat_participants table
CREATE TABLE chat_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id UUID NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    
    -- Type of participant
    participant_type TEXT NOT NULL CHECK (participant_type IN ('internal', 'external')),
    
    -- For internal (admin/rep in the system)
    admin_id UUID REFERENCES admins(id),
    
    -- For external (invited by email, no account)
    external_name TEXT,
    external_email TEXT,
    
    -- Invite token — used to generate the join URL for external parties
    -- Also used as the short-lived session credential after acceptance
    invite_token UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    
    -- Invite lifecycle
    status TEXT DEFAULT 'invited' CHECK (status IN ('invited', 'accepted', 'declined', 'removed')),
    invited_by_admin_id UUID NOT NULL REFERENCES admins(id),
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,
    
    -- Constraint: internal participants must have admin_id; external must have email
    CONSTRAINT internal_needs_admin CHECK (
        (participant_type = 'internal' AND admin_id IS NOT NULL) OR
        (participant_type = 'external' AND external_email IS NOT NULL AND external_name IS NOT NULL)
    )
);

CREATE INDEX idx_chat_participants_room ON chat_participants(room_id);
CREATE INDEX idx_chat_participants_token ON chat_participants(invite_token);
CREATE INDEX idx_chat_participants_admin ON chat_participants(admin_id);

-- 3. chat_messages table
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id UUID NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    
    -- One of these will be set, the other null, depending on who sent it
    sender_admin_id UUID REFERENCES admins(id),
    sender_participant_id UUID REFERENCES chat_participants(id),
    
    message TEXT NOT NULL,
    message_type TEXT DEFAULT 'text' CHECK (message_type IN ('text', 'file', 'system')),
    file_url TEXT, -- populated if message_type = 'file'
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_room ON chat_messages(room_id, created_at);

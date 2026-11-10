# Eximp & Cloves — Full Fix Specification
### 502 Remediation + Group Chat Architecture
_Prepared for handoff to implementation AI_

---

## Part 1 — 502 Bad Gateway: Root Cause Analysis

The app process never crashes (no restart events in Render). UptimeRobot keeps it warm. The 502s are **request-level timeouts** — Render's reverse proxy kills individual requests that hang past its 30-second threshold and returns a 502 to the browser. The app stays alive. This is why you see no event in the Render events tab.

The core problem is architectural: **the Supabase Python client (`supabase-py`) is entirely synchronous, but every route is declared `async def`**. When a synchronous Supabase call runs inside an async route, it occupies the event loop thread for the full duration of the network round trip to Supabase. During that time, FastAPI cannot process any other request. If two or more requests arrive concurrently (extremely common when the CRM dashboard loads — it fires multiple API calls simultaneously on page open), they queue behind each other. If the first one is slow (Supabase latency, London → wherever your Supabase instance lives), the queued requests accumulate wait time. Any request that accumulates enough wait to breach Render's 30-second timeout returns a 502.

**This is not a Supabase problem. It is not a Render problem. It is a Python async/sync boundary problem.**

---

### 502 Culprit Inventory

The following are every location in the codebase where synchronous blocking calls are made inside async context, ranked by severity.

---

#### Culprit 1 — `routers/analytics.py` → `get_kpis()` ⚠️ CRITICAL

This is the single most dangerous route in the codebase. Every time the main dashboard loads, this endpoint fires. It makes **8–10 sequential synchronous Supabase calls** in a single request, one after another, all blocking the event loop:

1. Invoices query (date-filtered)
2. Payments query (date-filtered)
3. Clients count query
4. Pending verifications count
5. All invoices query (unbounded — fetches entire table to resolve dynamic statuses in Python)
6. Previous period invoices query (for delta calculation)
7. Previous period payments query
8. Previous period refunds query
9. Previous period clients count

Each call is a separate network round trip to Supabase. If Supabase averages 150ms per query, this route takes over 1 second minimum — all of it blocking the event loop. On a slow Supabase day (400ms per query), it can hit 4 seconds, stalling every other concurrent request behind it.

The unbounded `all_inv_data` fetch (step 5) is especially dangerous — it fetches every invoice in the database into Python memory to iterate and resolve statuses. As the invoice table grows, this gets progressively worse.

**Fix required:** Wrap every `.execute()` call in `run_in_executor`. Move the dynamic status resolution to a Supabase RPC (SQL function) so it happens server-side. Add a `limit` and never fetch unbounded table scans into Python.

---

#### Culprit 2 — `scheduler.py` — All scheduled jobs ⚠️ CRITICAL

The scheduler runs inside the same FastAPI process on the same event loop. Every scheduled job calls synchronous Supabase operations directly:

- `sync_schedules_from_db()` runs every 10 minutes — synchronous DB call
- `process_appointment_reminders()` runs every 30 minutes — synchronous DB calls in a loop per appointment
- `process_support_nudges()` runs every 30 minutes — synchronous DB calls in a loop per ticket
- `run_scheduled_report()` — synchronous DB calls + PDF generation + Resend email send (all blocking)

**The collision scenario:** A user opens the CRM dashboard at exactly the moment `process_appointment_reminders` fires. The scheduler's synchronous Supabase calls block the event loop. The dashboard's `get_kpis()` call stacks behind it. Both are now waiting. The dashboard request hits 30 seconds and returns a 502, even though the scheduler job completes fine a second later.

**Fix required:** Every Supabase call inside a scheduler job must be wrapped with `run_in_executor`. Alternatively, use `asyncio.get_event_loop().run_in_executor(None, lambda: ...)` pattern throughout the scheduler, or migrate the scheduler jobs to use `asyncpg` / the async Supabase client.

---

#### Culprit 3 — `marketing_sequencer_engine.py` → `process_active_sequences()` ⚠️ HIGH

This runs every hour. It:
1. Fetches all active enrollments due today (potentially hundreds of rows)
2. For each enrollment, loops and makes multiple synchronous DB calls:
   - Fetch step details
   - Fetch previous step (for behavioral branching)
   - Check campaign_recipients interaction
   - Update enrollment status
   - Move to next step (another DB write)
3. Calls `send_marketing_email()` for each enrollment — which calls `resend.Emails.send()` synchronously (see Culprit 6)

If there are 50 active enrollments, this job makes 200–300 synchronous calls in a tight loop, potentially holding the event loop for 30+ seconds continuously.

`process_segment_triggers()` (also hourly) iterates all segment members with the same per-contact DB query pattern.

**Fix required:** All Supabase calls in these engines need `run_in_executor`. The per-contact inner loop is the worst offender — batch the DB reads before the loop, process in memory, batch-write updates after.

---

#### Culprit 4 — `marketing_scheduler.py` → `run_engagement_decay()` ⚠️ HIGH

The 90-day decay job fetches every contact with low engagement into Python (potentially thousands of rows), then updates each one individually in a loop:

```python
for contact in dormantres.data:
    new_score = contact["engagement_score"] // 2
    db.table("marketing_contacts").update({"engagement_score": new_score}).eq("id", contact["id"]).execute()
```

This is an N+1 update pattern. With 1,000 contacts, it fires 1,000 individual UPDATE statements, each blocking the event loop. This job runs at 2 AM but still occupies the process.

**Fix required:** Replace the Python loop with a single Supabase RPC call that does the halving in SQL. The 30-day and 180-day decay cases can similarly be collapsed into bulk SQL updates. This eliminates the loop entirely.

---

#### Culprit 5 — `routers/crm.py` → `get_contact_details()` ⚠️ HIGH

This endpoint fires whenever a rep opens a contact in the CRM. It makes **6 sequential synchronous Supabase calls** per open:

1. Client record
2. Invoices with joins
3. Payments with joins
4. Activity log (last 50)
5. Email logs (last 20)
6. Score calculation (in `score_lead()` which adds 4 more calls)

`score_all_leads()` is even worse — it fetches all clients, then for each client makes 4 more DB calls to compute scores. This is an O(N × 4) query pattern.

**Fix required:** `run_in_executor` on all calls. The score calculation should be pre-computed and stored, not recalculated live on every contact open.

---

#### Culprit 6 — `email_service.py` — All `resend.Emails.send()` calls ⚠️ HIGH

`resend.Emails.send()` is a **synchronous HTTP call** to the Resend API. It is called directly (without `await`, without `run_in_executor`) inside `async def` functions throughout `email_service.py`. There are approximately 20+ call sites. Each one blocks the event loop for the full duration of the Resend API round trip (typically 200–800ms, but can spike).

The pattern `await send_invoice_email(...)` gives the false appearance of async — the function is `async def` but internally calls `resend.Emails.send()` synchronously. Awaiting it does not make the Resend call non-blocking.

When a payment is recorded and triggers `send_receipt_email`, `send_commission_earned_email`, and `send_admin_alert_email` in sequence, that's 3 synchronous HTTP calls to Resend, all blocking the loop, before the payment endpoint returns.

**Fix required:** Every `resend.Emails.send(...)` call must be wrapped:
```python
loop = asyncio.get_event_loop()
res = await loop.run_in_executor(None, lambda: resend.Emails.send({...}))
```
Or migrate to `httpx.AsyncClient` with the Resend REST API directly.

---

#### Culprit 7 — `routers/support.py` → `get_ticket()` ⚠️ MEDIUM

This fires every time a rep opens a ticket. It makes 3 sequential synchronous calls:
1. Ticket + client + responses join
2. Admin names lookup for responses
3. Invoices for financial intelligence

Additionally, `create_notification()` (imported utility) is called synchronously inside `resolve_ticket()` — a synchronous DB write inside an async route.

**Fix required:** `run_in_executor` on all three queries. `create_notification` needs an async version.

---

#### Culprit 8 — `routers/crm_professional.py` → `list_all_documents()` ⚠️ MEDIUM

This endpoint makes sequential queries for invoices, then for each invoice loops to fetch additional data. Another N+1 pattern blocking the event loop.

---

#### Culprit 9 — `ws_support.py` — No keepalive ping ⚠️ MEDIUM

Render terminates idle WebSocket connections at ~55 seconds of no traffic. The current WS handler has no ping/pong mechanism. An admin who opens a ticket and reads it for 60 seconds without typing will have their WebSocket silently killed by Render's proxy. The frontend has no reconnect logic either — the socket object becomes dead and the admin gets no typing indicators or live refresh until they click away and back.

This doesn't cause a 502 directly but causes phantom disconnects and broken live-chat experience.

**Fix required:** Add a server-side ping loop that sends `{"type": "ping"}` every 30 seconds to all active connections. Add client-side `pong` response handling and auto-reconnect on close.

---

#### Culprit 10 — `routers/analytics.py` — Unbounded list fetches ⚠️ MEDIUM

`list_invoices()` in `routers/invoices.py` and `list_clients()` in `routers/clients.py` both fetch the entire table with no pagination limit. As data grows, these queries will return more rows and take longer, progressively worsening the blocking time per request.

**Fix required:** Add `limit` (default 50) and `offset` parameters to all list endpoints. The frontend should implement cursor-based or page-number pagination.

---

### The Universal Fix Pattern

Every `.execute()` call in every `async def` route and every scheduler job must be changed from:

```python
# BLOCKING — holds the event loop
res = db.table("support_tickets").select("*").execute()
```

To:

```python
# NON-BLOCKING — releases the event loop while waiting for DB
import asyncio
loop = asyncio.get_event_loop()
res = await loop.run_in_executor(
    None,
    lambda: db.table("support_tickets").select("*").execute()
)
```

A helper utility should be added to `database.py` to avoid repeating this pattern:

```python
# In database.py
import asyncio
from functools import partial

async def db_execute(query_fn):
    """
    Wraps a synchronous Supabase query in a thread executor so it 
    doesn't block FastAPI's async event loop.
    
    Usage:
        res = await db_execute(lambda: db.table("clients").select("*").execute())
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, query_fn)
```

Then every call site becomes:
```python
res = await db_execute(lambda: db.table("support_tickets").select("*").execute())
```

This single change, applied consistently, will eliminate the 502s.

---

### Priority Order for Fixes

1. `database.py` — add `db_execute` helper
2. `routers/analytics.py` — `get_kpis()` has the most sequential blocking calls and fires on every dashboard load
3. `scheduler.py` + `marketing_sequencer_engine.py` — scheduler collision is the hardest-to-reproduce 502 cause
4. `email_service.py` — wrap all `resend.Emails.send()` calls
5. `marketing_scheduler.py` — replace `run_engagement_decay` loop with SQL RPC
6. `routers/support.py`, `routers/crm.py`, `routers/crm_professional.py` — remaining heavy routes
7. `ws_support.py` — add keepalive ping

---

## Part 2 — Group Chat Architecture

### Overview

A sales rep can open a collaborative chat room on any support ticket. They can invite internal staff (other admins/reps already in the system) and external parties (lawyers, consultants, vendors — anyone with just an email address). External parties get a unique invitation link, do not need an account, and identify themselves by name. All parties must accept the invitation before entering. The client on the public support portal does **not** see the group chat — it is a private back-channel for the team and invited guests. Messages live in a dedicated table, separate from the existing `ticket_responses` thread.

---

### Database Schema

#### `chat_rooms` table
One room per ticket. A ticket can only have one active room at a time.

```sql
CREATE TABLE chat_rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    created_by_admin_id UUID NOT NULL REFERENCES admins(id),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticket_id) -- one room per ticket
);
```

#### `chat_participants` table
Tracks every person invited, their identity, their type, and their acceptance state. This is the core of the group chat feature.

```sql
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
```

#### `chat_messages` table
All messages in the room. Sender is identified by either their `admin_id` (internal) or `participant_id` (external). System-generated event messages use `message_type = 'system'`.

```sql
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
```

**System messages** are auto-inserted by the backend (never by the user) for events like:
- "Emeka invited John Doe (external) to this room"
- "Sarah accepted the invitation"
- "Marcus declined the invitation"  
- "John Doe was removed from this room"
- "Chat room was closed"

They render in the UI as neutral, italicised timeline markers between regular messages.

---

### API Endpoints

All endpoints must use `db_execute` (the async wrapper) on every DB call.

---

#### `POST /api/support/tickets/{ticket_id}/chat/create`
**Auth:** Admin JWT required.  
**Action:** Creates a `chat_rooms` record for the ticket. Inserts the creating rep as the first `chat_participants` record with `status = 'accepted'` and `participant_type = 'internal'`. Inserts a system message: "Rep Name opened this chat room."  
**Error:** Returns 409 if a room already exists for this ticket.  
**Returns:** `{ room_id, created_at }`

---

#### `POST /api/support/chat/{room_id}/invite`
**Auth:** Admin JWT required. Only participants with `status = 'accepted'` can invite others.  
**Body:**
```json
// Internal invite
{ "type": "internal", "admin_id": "uuid" }

// External invite  
{ "type": "external", "name": "John Doe", "email": "john@lawfirm.com" }
```
**Action (internal):**
- Creates `chat_participants` record with `participant_type = 'internal'`, `status = 'invited'`
- Calls `create_notification(admin_id, title="Chat Invitation", n_type="chat_invite", ref_id=room_id)` — the frontend handles this via `handleNotificationClick`
- Inserts system message: "Rep Name invited [Admin Full Name] to this room"

**Action (external):**
- Creates `chat_participants` record with `participant_type = 'external'`, `status = 'invited'`
- Generates join URL: `https://app.eximps-cloves.com/support/chat/join/{invite_token}`
- Sends invitation email via `email_service` with the join link, room context (ticket subject), and inviter's name
- Inserts system message: "Rep Name invited John Doe (external) to this room"

**Returns:** `{ participant_id, invite_token (for external only), status: "invited" }`

---

#### `POST /api/support/chat/join/{invite_token}`
**Auth:** None — public endpoint.  
**Action:**
- Validates `invite_token` exists and `status = 'invited'`
- Returns 410 Gone if token is for a `declined` or `removed` participant
- Returns 409 if already `accepted`
- Sets `status = 'accepted'`, sets `responded_at = NOW()`
- Inserts system message: "[Name] accepted the invitation"
- Notifies the inviting rep via `create_notification`

**Returns:** 
```json
{ 
  "room_id": "uuid",
  "ticket_id": "uuid", 
  "ticket_subject": "Help with contract",
  "participant_id": "uuid",
  "display_name": "John Doe",
  "session_token": "...",   // short-lived JWT scoped only to this room, used for WS auth and message POST
  "participants": [...],    // list of all accepted participants
  "messages": [...]         // last 50 messages
}
```

The `session_token` is a JWT with payload `{ sub: participant_id, room_id, type: "external_chat", exp: 24h }`. It is signed with the app's secret key and validated on the WS connect and `POST /message` endpoints.

---

#### `POST /api/support/chat/decline/{invite_token}`
**Auth:** None — public endpoint.  
**Action:** Sets `status = 'declined'`, sets `responded_at`. Inserts system message: "[Name] declined the invitation."  
**Returns:** `{ status: "declined" }`

---

#### `GET /api/support/chat/{room_id}`
**Auth:** Admin JWT **OR** valid `session_token` (external participant).  
**Action:** Validates the caller is an accepted participant of this room.  
**Returns:**
```json
{
  "room": { "id", "ticket_id", "ticket_subject", "status", "created_at" },
  "participants": [
    {
      "id", "participant_type", "display_name", "status", 
      "is_online": true/false   // based on active WS connections
    }
  ],
  "messages": [...]  // last 100, ordered ascending by created_at
}
```

---

#### `POST /api/support/chat/{room_id}/message`
**Auth:** Admin JWT **OR** valid `session_token`.  
**Body:** `{ "message": "text", "message_type": "text" }`  
**Action:**
- Validates sender is an accepted participant
- Inserts into `chat_messages` with the correct `sender_admin_id` or `sender_participant_id`
- Broadcasts via WebSocket (see WebSocket section below)
- Notifies all accepted participants who are **not currently connected** to the WS room via `create_notification` (internal) or does nothing (external — they have no notification inbox)

**Returns:** `{ message_id, created_at }`

---

#### `POST /api/support/chat/{room_id}/message/file`
**Auth:** Admin JWT **OR** valid `session_token`.  
**Body:** Multipart form — file upload.  
**Action:** Uploads file to `chat-media` Supabase Storage bucket, inserts message with `message_type = 'file'`, `file_url` set to the storage URL.  
**Returns:** `{ message_id, file_url, created_at }`

---

#### `DELETE /api/support/chat/{room_id}/participants/{participant_id}`
**Auth:** Admin JWT only. Only the room creator or a super_admin can remove participants.  
**Action:** Sets `status = 'removed'`. Inserts system message: "Rep Name removed [Name] from the room." If the removed participant has an active WS connection, sends them a `{"type": "removed"}` message over the socket before closing it.  
**Returns:** `{ status: "removed" }`

---

#### `POST /api/support/chat/{room_id}/close`
**Auth:** Admin JWT only. Room creator or super_admin.  
**Action:** Sets `chat_rooms.status = 'closed'`. Broadcasts `{"type": "room_closed"}` to all WS connections. Inserts system message: "Rep Name closed this chat room."  
**Returns:** `{ status: "closed" }`

---

### WebSocket Changes (`ws_support.py`)

The existing `ConnectionManager` and `/api/ws/support/{ticket_id}` endpoint should remain unchanged (it handles the public client-side ticket chat). A new manager and endpoint are added for the group chat.

#### New WS endpoint
```
wss://host/api/ws/chat/{room_id}?token={jwt_or_session_token}
```

The `token` query parameter is mandatory. On connect:
1. Validate the token (admin JWT or external session_token)
2. Confirm the resolved participant is `accepted` in this `room_id`
3. If valid: accept the connection, store it in the connection map with identity metadata
4. If invalid: close with code 4001

#### Connection map structure
The existing map `Dict[str, List[WebSocket]]` must become `Dict[str, List[ConnectionInfo]]` where:
```python
@dataclass
class ConnectionInfo:
    websocket: WebSocket
    participant_id: str        # chat_participants.id
    display_name: str          # for broadcast payloads
    participant_type: str      # 'internal' or 'external'
    admin_id: Optional[str]    # set if internal
```

#### Broadcast payload schema
All message broadcasts must include full sender context so the frontend renders without a round-trip:
```json
{
  "type": "message",
  "message_id": "uuid",
  "room_id": "uuid",
  "sender_name": "Emeka Okafor",
  "sender_type": "internal",
  "message": "I've reviewed the contract",
  "message_type": "text",
  "file_url": null,
  "created_at": "2026-04-10T10:30:00Z"
}
```

System events broadcast as:
```json
{ "type": "system", "message": "John Doe accepted the invitation", "created_at": "..." }
```

Presence events broadcast as:
```json
{ "type": "presence", "event": "joined", "participant_id": "uuid", "display_name": "John Doe" }
{ "type": "presence", "event": "left", "participant_id": "uuid", "display_name": "John Doe" }
```

#### Keepalive ping (fixes Culprit 9)
The new chat WS handler must include a ping loop:
```python
async def support_chat_websocket(websocket: WebSocket, room_id: str, token: str):
    # ... validate and connect ...
    
    ping_task = asyncio.create_task(ping_loop(websocket))
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "pong":
                continue  # keepalive acknowledged, do nothing
            # handle other message types...
    except WebSocketDisconnect:
        ping_task.cancel()
        manager.disconnect(websocket, room_id)
        await manager.broadcast({"type": "presence", "event": "left", ...}, room_id)

async def ping_loop(websocket: WebSocket):
    while True:
        await asyncio.sleep(30)
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            break
```

Apply the same ping loop to the existing `/api/ws/support/{ticket_id}` endpoint.

---

### Notification Changes

#### New notification type: `chat_invite`
Internal participants receive a notification when invited:
```python
create_notification(
    admin_id=invited_admin_id,
    title="You've been invited to a chat",
    message=f"{inviter_name} invited you to the room for: {ticket_subject}",
    n_type="chat_invite",
    ref_id=room_id
)
```

#### `handleNotificationClick` in `professional_crm.html`
A new `chat_invite` case needs to be added alongside the existing `support` case:
```javascript
async function handleNotificationClick(id, type, refId) {
    await fetch(`/api/notifications/${id}/read`, { method: 'PATCH', headers: ... });
    
    if (type === 'support' && refId) {
        switchView('support-desk');
        viewTicket(refId);  // existing behaviour
    } else if (type === 'chat_invite' && refId) {
        // refId is room_id here
        switchView('support-desk');
        openChatRoomById(refId);  // new function — fetches room, finds ticket, opens chat panel
    }
    
    document.getElementById('notif-dropdown').classList.remove('active');
}
```

#### New message notifications
When a message is posted, notify all accepted participants who are NOT currently in the WS room:

```python
# In POST /chat/{room_id}/message handler
connected_participant_ids = chat_manager.get_connected_participant_ids(room_id)
for participant in accepted_participants:
    if participant["id"] not in connected_participant_ids:
        if participant["participant_type"] == "internal" and participant["admin_id"]:
            create_notification(
                admin_id=participant["admin_id"],
                title="New message in chat",
                message=f"{sender_name}: {message[:80]}",
                n_type="chat_invite",  # reuse type — same navigation handler
                ref_id=room_id
            )
        # External participants have no in-app inbox — email notification is optional
```

---

### Frontend Changes (`professional_crm.html`)

#### In the ticket detail panel
Add a **"Group Chat"** tab alongside the existing ticket thread. The tab should show:

**When no room exists for this ticket:**
- A "Start Group Chat" button
- On click: calls `POST /api/support/tickets/{ticket_id}/chat/create`, then renders the chat panel

**When a room exists:**
- Participant list on the right side with status badges: `accepted` (green), `invited` (amber), `declined` (red), `removed` (grey)
- An "Invite" button that opens a modal with:
  - Radio toggle: "Internal Staff" / "External Party"
  - If internal: searchable dropdown of admins/reps
  - If external: name field + email field
  - "Send Invitation" button
- Message thread area:
  - System messages rendered as centred, italicised, grey text (e.g. `— Emeka invited John Doe —`)
  - Internal messages aligned right with sender name above
  - External messages aligned left with sender name above, a small "External" badge
  - File messages show a download link
- Input area with send button and file attach button
- "Close Chat Room" button (visible to room creator and super_admin only)

#### External join page (new template)
New route in `main.py`: `GET /support/chat/join/{invite_token}` → renders new template `templates/chat_join.html`

This page:
1. Calls `GET /api/support/chat/join-info/{invite_token}` (public endpoint, returns inviter name, ticket subject, status — but NOT the session token yet)
2. Displays: "Emeka Okafor has invited you to a support chat about: [ticket subject]"
3. Shows the external party's pre-filled name (from invite record)
4. Two buttons: "Accept & Join" and "Decline"
5. On "Accept & Join": calls `POST /api/support/chat/join/{invite_token}`, receives session_token, then renders the chat interface in the same page using the session_token for WS auth and message POSTs
6. On "Decline": calls `POST /api/support/chat/decline/{invite_token}`, shows a simple "You have declined the invitation" confirmation

The chat interface on this page is a standalone implementation (no CRM dashboard wrapper) — just the message thread, participant list, and input box.

---

### What the Previous AI's Plan Already Covers (and What Changes)

The previous session planned:
- `notify_privileged_admins()` utility — **still needed, build as planned**
- `BackgroundTasks` for `create_ticket` notifications — **still needed, build as planned**
- `create_ticket` never fires notification — **still the bug, fix as planned**
- `client-reply` broken fallback — **still the bug, fix as planned**
- `chat_sessions` + `chat_messages` tables — **replace `chat_sessions` with `chat_rooms` + `chat_participants` as defined above; `chat_messages` schema is compatible**
- `initiate-chat` endpoint (dead call in frontend at line 1819) — **replace with `POST /chat/create` + `POST /chat/invite` flow; remove the dead frontend reference**
- `chat-media` Supabase Storage bucket — **still needed; create with authenticated access, not fully public**
- `handleNotificationClick` `"chat"` case — **implement as `"chat_invite"` case as defined above**

---

### Deployment Checklist (Before Going Live)

1. Run the new migration SQL (`chat_rooms`, `chat_participants`, `chat_messages` tables)
2. Create `chat-media` bucket in Supabase Storage — set to **authenticated access only**, not public. Use signed URLs for file retrieval.
3. Add `chat_rooms`, `chat_participants`, `chat_messages` RLS policies — service role key bypasses RLS so backend is fine, but ensure no public read access
4. Deploy `db_execute` helper to `database.py` first, before any route changes
5. Apply `run_in_executor` to analytics and scheduler — these are the 502-causing changes
6. Wrap all `resend.Emails.send()` calls in `email_service.py`
7. Replace engagement decay loop in `marketing_scheduler.py` with SQL RPC
8. Add WS keepalive to both the existing `ws_support.py` and the new chat WS handler
9. Update `handleNotificationClick` in `professional_crm.html` before deploying notification changes
10. Test the external join flow end-to-end before releasing — the session_token path is the most novel piece and must be validated carefully

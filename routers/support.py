from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Request
from typing import List, Optional
from pydantic import BaseModel
from database import get_db, db_execute
from models import SupportTicketCreate, SupportTicketUpdate, TicketResponseCreate, ChatInviteRequest, ChatMessageRequest
import uuid
import jwt
from datetime import datetime, timedelta
import os
from routers.auth import verify_token, verify_token_optional
from routers.notifications import create_notification
from routers.ws_support import chat_manager
from email_service import send_chat_invitation_email
from datetime import datetime
from routers.sync_utils import associate_client_with_rep
import json

router = APIRouter()

@router.post("/initiate-chat")
async def initiate_chat(client_id: str, current_admin=Depends(verify_token)):
    """
    Bridge endpoint to start a Group Chat room for a lead in the CRM.
    """
    db = get_db()
    admin_id = current_admin["sub"]
    
    # 1. Verify Client
    client_res = await db_execute(lambda: db.table("clients").select("*").eq("id", client_id).execute())
    if not client_res.data:
        raise HTTPException(status_code=404, detail="Client not found")
    client = client_res.data[0]
    
    # 2. Check if a room already exists for a ticket related to this client
    # For simplicity, we create a new ticket called "Pipeline Chat" if none exists recently
    ticket_payload = {
        "subject": f"Chat with {client['full_name']}",
        "description": f"Direct chat initiated from Sales Pipeline by {current_admin.get('full_name', 'Admin')}",
        "category": "property",
        "priority": "medium",
        "client_id": client_id,
        "contact_email": client["email"],
        "contact_name": client["full_name"],
        "status": "open",
        "assigned_admin_id": admin_id
    }
    
    ticket_res = await db_execute(lambda: db.table("support_tickets").insert(ticket_payload).execute())
    ticket_id = ticket_res.data[0]["id"]
    
    # 3. Create Chat Room
    room_res = await db_execute(lambda: db.table("chat_rooms").insert({
        "ticket_id": ticket_id,
        "created_by_admin_id": admin_id
    }).execute())
    room_id = room_res.data[0]["id"]
    
    # 4. Add Admin as Internal Participant (Accepted)
    await db_execute(lambda: db.table("chat_participants").insert({
        "room_id": room_id,
        "participant_type": "internal",
        "admin_id": admin_id,
        "status": "accepted",
        "invited_by_admin_id": admin_id
    }).execute())
    
    # 5. Add Client as External Participant (Invited)
    client_part_res = await db_execute(lambda: db.table("chat_participants").insert({
        "room_id": room_id,
        "participant_type": "external",
        "external_name": client["full_name"],
        "external_email": client["email"],
        "status": "invited",
        "invited_by_admin_id": admin_id
    }).execute())
    invite_token = client_part_res.data[0]["invite_token"]
    
    return {
        "room_id": room_id,
        "portal_url": f"/join?token={invite_token}"
    }

@router.post("/tickets")
async def create_ticket(data: SupportTicketCreate):
    """
    Public-facing endpoint for the website floating widget.
    Can be used by both logged-in clients and anonymous visitors.
    """
    db = get_db()
    
    ticket_payload = {
        "subject": data.subject,
        "description": data.description,
        "category": data.category,
        "priority": data.priority,
        "client_id": data.client_id,
        "contact_email": data.contact_email,
        "contact_name": data.contact_name,
        "status": "open",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Check if this email belongs to a VIP client to auto-escalate priority
    client_res = await db_execute(lambda: db.table("clients").select("id").eq("email", data.contact_email).execute())
    if client_res.data:
        client_id = client_res.data[0]["id"]
        ticket_payload["client_id"] = client_id
        
        # Calculate LTV
        inv_res = await db_execute(lambda: db.table("invoices").select("amount").eq("client_id", client_id).eq("status", "paid").execute())
        if inv_res.data:
            total_ltv = sum(i["amount"] for i in inv_res.data)
            if total_ltv >= 10_000_000:
                ticket_payload["priority"] = "high"
                if not ticket_payload["subject"].startswith("[VIP]"):
                    ticket_payload["subject"] = f"[VIP] {ticket_payload['subject']}"
    
    res = await db_execute(lambda: db.table("support_tickets").insert(ticket_payload).execute())
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create support ticket")
    
    return {"message": "Ticket created successfully", "ticket_id": res.data[0]["id"]}

@router.get("/tickets")
async def list_tickets(status: Optional[str] = None, current_admin=Depends(verify_token)):
    """Admin-only view for the CRM Support Hub."""
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])

    # Use !inner to ensure we only return tickets where the client exists and matches any rep filters
    query = db.table("support_tickets").select("*, clients!inner(full_name, email, assigned_rep_id)")
    
    if status:
        query = query.eq("status", status)
    
    if not is_privileged:
        query = query.filter("clients.assigned_rep_id", "eq", admin_id)
        
    res = await db_execute(lambda: query.order("created_at", desc=True).execute())
    return res.data

@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])

    # Fetch ticket and responses
    res = await db_execute(lambda: db.table("support_tickets")\
        .select("*, clients(*), ticket_responses(*)")\
        .eq("id", ticket_id)\
        .execute())
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket = res.data[0]

    # RBAC Enforcement: Check if rep belongs to this client
    if not is_privileged:
        client = ticket.get("clients")
        if not client or client.get("assigned_rep_id") != admin_id:
            raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this client.")

    
    # Manually join admin names for responses
    if ticket.get("ticket_responses"):
        admin_ids = list(set(r["admin_id"] for r in ticket["ticket_responses"] if r.get("admin_id")))
        if admin_ids:
            admins_res = await db_execute(lambda: db.table("admins").select("id, full_name").in_("id", admin_ids).execute())
            admin_map = {a["id"]: a["full_name"] for a in admins_res.data}
            for r in ticket["ticket_responses"]:
                if r.get("admin_id"):
                    r["admins"] = {"full_name": admin_map.get(r["admin_id"], "Unknown Admin")}
    
    # Financial Intelligence
    ticket["financial_intel"] = {"total_deals": 0, "total_paid": 0, "balance_due": 0}
    if ticket.get("client_id"):
        inv_res = await db_execute(lambda: db.table("invoices").select("amount, status").eq("client_id", ticket["client_id"]).execute())
        if inv_res.data:
            ticket["financial_intel"]["total_deals"] = len(inv_res.data)
            ticket["financial_intel"]["total_paid"] = sum(i["amount"] for i in inv_res.data if i["status"] == "paid")
            ticket["financial_intel"]["balance_due"] = sum(i["amount"] for i in inv_res.data if i["status"] in ["unpaid", "partial"])

    return ticket

@router.patch("/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, data: SupportTicketUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    update_dict = {k: v for k, v in data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow().isoformat()
    
    res = await db_execute(lambda: db.table("support_tickets").update(update_dict).eq("id", ticket_id).execute())
    return res.data[0]

@router.post("/tickets/{ticket_id}/respond")
async def respond_to_ticket(ticket_id: str, data: TicketResponseCreate, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    """Add a response to a ticket and optionally notify the client."""
    db = get_db()
    
    response_payload = {
        "ticket_id": ticket_id,
        "message": data.message,
        "admin_id": current_admin["sub"],
        "is_internal": data.is_internal,
        "created_at": datetime.utcnow().isoformat()
    }
    
    res = await db_execute(lambda: db.table("ticket_responses").insert(response_payload).execute())
    
    # Update ticket status and track last admin response
    await db_execute(lambda: db.table("support_tickets").update({
        "status": "resolved" if "resolved" in data.message.lower() else "pending", 
        "updated_at": datetime.utcnow().isoformat(),
        "last_admin_response_at": datetime.utcnow().isoformat(),
        "followup_sent_at": None # Reset nudge timer
    }).eq("id", ticket_id).execute())

    # Notify Client if NOT internal
    if not data.is_internal:
        from email_service import send_support_response_email
        ticket_res = await db_execute(lambda: db.table("support_tickets").select("*").eq("id", ticket_id).execute())
        if ticket_res.data:
            background_tasks.add_task(send_support_response_email, ticket_res.data[0], data.message)
    
    return {"message": "Response added", "data": res.data[0]}

@router.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("support_tickets").update({
        "status": "resolved",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", ticket_id).execute())
    
    # Create notification for audit (optional)
    await create_notification(
        admin_id=current_admin["sub"],
        title="Ticket Resolved",
        message=f"You resolved ticket #{ticket_id[:8]}",
        n_type="support",
        ref_id=ticket_id
    )
    
    return res.data[0]

@router.post("/tickets/{ticket_id}/client-reply")
async def client_reply_to_ticket(ticket_id: str, data: TicketResponseCreate):
    """
    Public endpoint to simulate a client replying via a portal.
    Triggers a real-time notification for the assigned admin.
    """
    db = get_db()
    
    # Verify ticket exists
    ticket_res = await db_execute(lambda: db.table("support_tickets").select("subject, assigned_admin_id").eq("id", ticket_id).execute())
    if not ticket_res.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket = ticket_res.data[0]
    
    response_payload = {
        "ticket_id": ticket_id,
        "message": data.message,
        "admin_id": None, # Null admin indicates client reply
        "is_internal": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    res = await db_execute(lambda: db.table("ticket_responses").insert(response_payload).execute())
    
    # Re-open ticket and clear admin response tracking
    await db_execute(lambda: db.table("support_tickets").update({
        "status": "open",
        "updated_at": datetime.utcnow().isoformat(),
        "last_admin_response_at": None,
        "client_typing_at": None
    }).eq("id", ticket_id).execute())
    
    # TRIGGER NOTIFICATION
    assigned_to = ticket.get("assigned_admin_id")
    if not assigned_to:
        # If no one assigned, notify all super admins? For now, we'll try to find any admin.
        first_admin = await db_execute(lambda: db.table("admins").select("id").limit(1).execute())
        assigned_to = first_admin.data[0]["id"] if first_admin.data else None

    if assigned_to:
        await create_notification(
            admin_id=assigned_to,
            title="New Client Response",
            message=f"Client replied to: {ticket['subject']}",
            n_type="support",
            ref_id=ticket_id
        )
    
    return {"status": "ok", "message": "Reply recorded & staff notified"}

@router.get("/portal/{ticket_id}")
async def get_portal_ticket(ticket_id: str):
    """
    Public endpoint for the Client Portal.
    Strictly filters out internal responses for security.
    """
    db = get_db()
    
    # Fetch ticket
    res = await db_execute(lambda: db.table("support_tickets").select("*, clients(full_name, email)").eq("id", ticket_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket = res.data[0]
    
    # Fetch only PUBLIC responses
    resp_res = await db_execute(lambda: db.table("ticket_responses")\
        .select("*")\
        .eq("ticket_id", ticket_id)\
        .eq("is_internal", False)\
        .order("created_at", desc=False)\
        .execute())
    
    ticket["ticket_responses"] = resp_res.data
    
    # Manually join admin names (limited info)
    admin_ids = list(set(r["admin_id"] for r in ticket["ticket_responses"] if r.get("admin_id")))
    if admin_ids:
        admins_res = await db_execute(lambda: db.table("admins").select("id, full_name").in_("id", admin_ids).execute())
        admin_map = {a["id"]: a["full_name"] for a in admins_res.data}
        for r in ticket["ticket_responses"]:
            if r.get("admin_id"):
                r["admins"] = {"full_name": admin_map.get(r["admin_id"], "Support Agent")}
                
    return ticket

@router.get("/stats")
async def get_support_stats(current_admin=Depends(verify_token)):
    """Stats for the CRM Support Dashboard cards."""
    db = get_db()
    res = await db_execute(lambda: db.table("support_tickets").select("status").execute())
    tickets = res.data or []
    
    stats = {
        "total": len(tickets),
        "open": len([t for t in tickets if t["status"] == "open"]),
        "pending": len([t for t in tickets if t["status"] == "pending"]),
        "resolved": len([t for t in tickets if t["status"] == "resolved"]),
    }
    return stats

@router.post("/tickets/{ticket_id}/typing")
async def update_typing_status(ticket_id: str, is_typing: bool, is_admin: bool = False):
    """Update the typing timestamp for the chat participant."""
    try:
        from datetime import datetime
        db = get_db()
        field = "admin_typing_at" if is_admin else "client_typing_at"
        # If is_typing is true, set to now, else set to null
        val = datetime.utcnow().isoformat() if is_typing else None
        
        await db_execute(lambda: db.table("support_tickets").update({field: val}).eq("id", ticket_id).execute())
        return {"status": "ok"}
    except Exception as e:
        print(f"Error updating typing status: {e}")
        return {"status": "error", "message": str(e)}


# ==========================================
# GROUP CHAT ARCHITECTURE (Phase 2)
# ==========================================

def _create_session_token(participant_id: str, room_id: str) -> str:
    payload = {
        "sub": participant_id,
        "room_id": room_id,
        "type": "external_chat",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET", "super-secret"), algorithm="HS256")

def _verify_session_token(token: str) -> dict:
    try:
        return jwt.decode(token, os.getenv("JWT_SECRET", "super-secret"), algorithms=["HS256"])
    except:
        return None

async def _resolve_chat_auth(request: Request, current_admin: Optional[dict] = None):
    """
    Resolves identity for chat. Supports:
    1. Admin JWT (via VerifyToken dependency)
    2. Session Token (via Authorization header or Cookie)
    """
    db = get_db()
    
    if current_admin:
        admin_id = current_admin["sub"]
        admin_email = current_admin.get("email")
        
        # IDENTITY BRIDGE: Ensure the ID exists in our custom 'admins' table
        check = await db_execute(lambda: db.table("admins").select("id, full_name").eq("id", admin_id).execute())
        
        if not check.data and admin_email:
            # If ID mismatch (e.g. Supabase Auth ID in token), lookup by email
            print(f"Auth Bridge: ID {admin_id} not found in 'admins'. Attempting email lookup for {admin_email}")
            bridge = await db_execute(lambda: db.table("admins").select("id, full_name").eq("email", admin_email).execute())
            if bridge.data:
                admin_id = bridge.data[0]["id"]
                current_admin["full_name"] = bridge.data[0]["full_name"]
            else:
                raise HTTPException(status_code=403, detail="Your account is not registered in the team management system.")

        return {
            "participant_id": None,
            "admin_id": admin_id,
            "name": current_admin.get("full_name") or current_admin.get("name", "Admin"),
            "type": "internal"
        }
    
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    if token:
        payload = _verify_session_token(token)
        if payload and payload.get("type") == "external_chat":
            part = await db_execute(lambda: db.table("chat_participants").select("id, external_name").eq("id", payload["sub"]).execute())
            if part.data:
                return {
                    "participant_id": payload["sub"],
                    "admin_id": None,
                    "name": part.data[0]["external_name"],
                    "type": "external"
                }
    
    raise HTTPException(status_code=401, detail="Authentication required for chat")

@router.post("/tickets/{ticket_id}/chat/create")
async def create_chat_room(ticket_id: str, current_admin=Depends(verify_token)):
    if not ticket_id or ticket_id == "null":
        raise HTTPException(status_code=400, detail="A valid ticket ID is required to create a chat room.")
    
    db = get_db()
    # 1. Check if room exists
    existing = await db_execute(lambda: db.table("chat_rooms").select("id").eq("ticket_id", ticket_id).execute())
    if existing.data:
        raise HTTPException(status_code=409, detail="A chat room already exists for this ticket.")
    
    # 2. Create room
    room_res = await db_execute(lambda: db.table("chat_rooms").insert({
        "ticket_id": ticket_id,
        "created_by_admin_id": current_admin["sub"]
    }).execute())
    room_id = room_res.data[0]["id"]
    
    # 3. Add creator as first participant
    await db_execute(lambda: db.table("chat_participants").insert({
        "room_id": room_id,
        "participant_type": "internal",
        "admin_id": current_admin["sub"],
        "status": "accepted",
        "invited_by_admin_id": current_admin["sub"],
        "responded_at": datetime.utcnow().isoformat()
    }).execute())
    
    # 4. Insert System msg
    await db_execute(lambda: db.table("chat_messages").insert({
        "room_id": room_id,
        "message": f"{current_admin.get('full_name', 'A representative')} opened this chat room.",
        "message_type": "system"
    }).execute())
    
    return {"room_id": room_id, "created_at": room_res.data[0]["created_at"]}

@router.post("/chat/{room_id}/invite")
async def invite_to_chat(room_id: str, req: ChatInviteRequest, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    
    # Validation
    is_part = await db_execute(lambda: db.table("chat_participants").select("id").eq("room_id", room_id).eq("admin_id", current_admin["sub"]).eq("status", "accepted").execute())
    if not is_part.data:
        raise HTTPException(status_code=403, detail="You must be an active participant to invite others.")
        
    part_payload = {
        "room_id": room_id,
        "participant_type": req.type,
        "invited_by_admin_id": current_admin["sub"],
        "status": "invited"
    }

    inviter_name = current_admin.get("full_name", "A representative")
    
    if req.type == "internal":
        if not req.admin_id: raise HTTPException(status_code=400, detail="admin_id required for internal invites")
        part_payload["admin_id"] = req.admin_id
        
        # Check if already invited
        exist = await db_execute(lambda: db.table("chat_participants").select("id").eq("room_id", room_id).eq("admin_id", req.admin_id).execute())
        if exist.data: raise HTTPException(status_code=409, detail="Already a participant")
        
        res = await db_execute(lambda: db.table("chat_participants").insert(part_payload).execute())
        
        # Notify
        admin_res = await db_execute(lambda: db.table("admins").select("full_name").eq("id", req.admin_id).execute())
        recipient_name = admin_res.data[0]["full_name"] if admin_res.data else "Admin"
        
        await create_notification(req.admin_id, "Chat Invitation", f"{inviter_name} invited you to a chat room", "chat_invite", room_id)
        sys_msg = f"{inviter_name} invited {recipient_name} to this room"
        
    else: # external
        if not req.email or not req.name: raise HTTPException(status_code=400, detail="name and email required for external invites")
        part_payload["external_name"] = req.name
        part_payload["external_email"] = req.email
        
        res = await db_execute(lambda: db.table("chat_participants").insert(part_payload).execute())
        sys_msg = f"{inviter_name} invited {req.name} (external) to this room"
        
        invite_token = res.data[0]["invite_token"]
        join_url = f"https://app.eximps-cloves.com/support/chat/join/{invite_token}"
        
        # Get ticket subject for context
        room_res = await db_execute(lambda: db.table("chat_rooms").select("ticket_id, support_tickets(subject)").eq("id", room_id).execute())
        ticket_subject = room_res.data[0]["support_tickets"]["subject"] if room_res.data else "Support Ticket"
        
        background_tasks.add_task(send_chat_invitation_email, req.email, req.name, inviter_name, join_url, ticket_subject)

    await db_execute(lambda: db.table("chat_messages").insert({
        "room_id": room_id, "message": sys_msg, "message_type": "system"
    }).execute())
    
    return res.data[0]

@router.post("/chat/join/{invite_token}")
async def join_chat(invite_token: str):
    db = get_db()
    res = await db_execute(lambda: db.table("chat_participants").select("*, chat_rooms(id, ticket_id)").eq("invite_token", invite_token).execute())
    if not res.data: raise HTTPException(status_code=404, detail="Invalid token")
    
    part = res.data[0]
    if part["status"] in ["declined", "removed"]: raise HTTPException(status_code=410, detail="Invitation no longer valid")
    
    # IDEMPOTENT JOIN: If already accepted, skip the status update and system message
    is_new_join = part["status"] != "accepted"
    
    if is_new_join:
        # Mark accepted
        await db_execute(lambda: db.table("chat_participants").update({
            "status": "accepted", "responded_at": datetime.utcnow().isoformat()
        }).eq("id", part["id"]).execute())
    
    room_id = part["room_id"]
    display_name = part["external_name"] if part["participant_type"] == "external" else "An Admin"
    if part["participant_type"] == "internal":
        admin_res = await db_execute(lambda: db.table("admins").select("full_name").eq("id", part["admin_id"]).execute())
        if admin_res.data: display_name = admin_res.data[0]["full_name"]
    
    if is_new_join:
        await db_execute(lambda: db.table("chat_messages").insert({
            "room_id": room_id, "message": f"{display_name} accepted the invitation", "message_type": "system"
        }).execute())
        
        await create_notification(part["invited_by_admin_id"], "Chat Invite Accepted", f"{display_name} joined the chat", "chat_invite", room_id)
    
    # Construct response
    ticket_id = part["chat_rooms"]["ticket_id"]
    t_res = await db_execute(lambda: db.table("support_tickets").select("subject").eq("id", ticket_id).execute())
    
    participants_res = await db_execute(lambda: db.table("chat_participants").select("*").eq("room_id", room_id).eq("status", "accepted").execute())
    msgs_res = await db_execute(lambda: db.table("chat_messages").select("*").eq("room_id", room_id).order("created_at", desc=True).limit(50).execute())
    
    return {
        "room_id": room_id,
        "ticket_id": ticket_id,
        "ticket_subject": t_res.data[0]["subject"] if t_res.data else "Ticket",
        "participant_id": part["id"],
        "display_name": display_name,
        "session_token": _create_session_token(part["id"], room_id),
        "participants": participants_res.data,
        "messages": msgs_res.data[::-1]
    }

@router.post("/chat/decline/{invite_token}")
async def decline_chat(invite_token: str):
    db = get_db()
    res = await db_execute(lambda: db.table("chat_participants").select("*").eq("invite_token", invite_token).execute())
    if not res.data: raise HTTPException(status_code=404)
    part = res.data[0]
    
    await db_execute(lambda: db.table("chat_participants").update({
        "status": "declined", "responded_at": datetime.utcnow().isoformat()
    }).eq("id", part["id"]).execute())
    
    name = part["external_name"] if part["participant_type"]=="external" else "Participant"
    await db_execute(lambda: db.table("chat_messages").insert({
        "room_id": part["room_id"], "message": f"{name} declined the invitation", "message_type": "system"
    }).execute())
    return {"status": "declined"}

@router.get("/chat/{room_id}")
async def get_chat_room(room_id: str, token: str = None, current_admin=Depends(verify_token)):
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])

    # Fetch room with ticket and client info for RBAC check
    room_res = await db_execute(lambda: db.table("chat_rooms")\
        .select("*, support_tickets(id, client_id, clients(assigned_rep_id))")\
        .eq("id", room_id)\
        .execute())
    
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    room = room_res.data[0]

    # RBAC Enforcement
    if not is_privileged:
        ticket = room.get("support_tickets")
        client = ticket.get("clients") if ticket else None
        if not client or client.get("assigned_rep_id") != admin_id:
            raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this client's chat room.")

    
    parts = await db_execute(lambda: db.table("chat_participants").select("*").eq("room_id", room_id).execute())
    msgs = await db_execute(lambda: db.table("chat_messages").select("*").eq("room_id", room_id).order("created_at", desc=False).limit(100).execute())
    
    return {
        "room": room,
        "participants": parts.data,
        "messages": msgs.data
    }

@router.post("/chat/{room_id}/message")
async def post_chat_message(room_id: str, req: ChatMessageRequest, request: Request, current_admin=Depends(verify_token_optional)):
    db = get_db()
    auth = await _resolve_chat_auth(request, current_admin)
    
    # 1. Verify participant belongs to room
    participant_id = None
    if auth["type"] == "internal":
        part_res = await db_execute(lambda: db.table("chat_participants").select("id").eq("room_id", room_id).eq("admin_id", auth["admin_id"]).eq("status", "accepted").execute())
        if not part_res.data:
            # AUTO-JOIN: If an admin/rep is messaging but not yet a participant, add them automatically
            admin_info = await db_execute(lambda: db.table("admins").select("full_name").eq("id", auth["admin_id"]).execute())
            if admin_info.data:
                auth["name"] = admin_info.data[0]["full_name"]
            
            new_part = await db_execute(lambda: db.table("chat_participants").insert({
                "room_id": room_id,
                "participant_type": "internal",
                "admin_id": auth["admin_id"],
                "status": "accepted",
                "invited_by_admin_id": auth["admin_id"]
            }).execute())
            participant_id = new_part.data[0]["id"]
            
            # Broadcast their arrival
            await chat_manager.broadcast({
                "type": "presence", "event": "joined", "participant_id": participant_id, "display_name": auth["name"]
            }, room_id)
        else:
            participant_id = part_res.data[0]["id"]
    else:
        part_res = await db_execute(lambda: db.table("chat_participants").select("id").eq("room_id", room_id).eq("id", auth["participant_id"]).eq("status", "accepted").execute())
        if not part_res.data:
            raise HTTPException(status_code=403, detail="You are not an active participant in this room")
        participant_id = part_res.data[0]["id"]
    
    # 2. Insert message
    msg_payload = {
        "room_id": room_id,
        "message": req.message,
        "message_type": req.message_type
    }
    if auth["type"] == "internal":
        msg_payload["sender_admin_id"] = auth["admin_id"]
    else:
        msg_payload["sender_participant_id"] = auth["participant_id"]
        
    res = await db_execute(lambda: db.table("chat_messages").insert(msg_payload).execute())
    msg_data = res.data[0]
    
    # 3. Broadcast to WS
    await chat_manager.broadcast({
        "type": "message",
        "message_id": msg_data["id"],
        "room_id": room_id,
        "sender_name": auth["name"],
        "sender_type": auth["type"],
        "message": req.message,
        "message_type": req.message_type,
        "file_url": None,
        "created_at": msg_data["created_at"]
    }, room_id)
    
    return msg_data

@router.post("/chat/{room_id}/message/file")
async def upload_chat_file(room_id: str, request: Request, file: UploadFile = File(...), current_admin=Depends(verify_token_optional)):
    db = get_db()
    auth = await _resolve_chat_auth(request, current_admin)
    
    # Verify participation (redundant but safe)
    if auth["type"] == "internal":
        part_res = await db_execute(lambda: db.table("chat_participants").select("id").eq("room_id", room_id).eq("admin_id", auth["admin_id"]).eq("status", "accepted").execute())
    else:
        part_res = await db_execute(lambda: db.table("chat_participants").select("id").eq("room_id", room_id).eq("id", auth["participant_id"]).eq("status", "accepted").execute())
    
    if not part_res.data: raise HTTPException(status_code=403)

    # 1. Upload to Supabase Storage
    import uuid
    file_ext = file.filename.split(".")[-1]
    file_path = f"{room_id}/{uuid.uuid4()}.{file_ext}"
    file_content = await file.read()
    
    # Using personal access token or admin key for storage if needed, 
    # but here we assume the supabase client has permissions
    storage_res = await db_execute(lambda: db.storage.from_("chat-media").upload(file_path, file_content))
    file_url = db.storage.from_("chat-media").get_public_url(file_path)

    # 2. Insert message
    msg_payload = {
        "room_id": room_id,
        "message": f"Sent a file: {file.filename}",
        "message_type": "file",
        "file_url": file_url
    }
    if auth["type"] == "internal":
        msg_payload["sender_admin_id"] = auth["admin_id"]
    else:
        msg_payload["sender_participant_id"] = auth["participant_id"]
        
    res = await db_execute(lambda: db.table("chat_messages").insert(msg_payload).execute())
    msg_data = res.data[0]

    # 3. Broadcast
    await chat_manager.broadcast({
        "type": "message",
        "message_id": msg_data["id"],
        "room_id": room_id,
        "sender_name": auth["name"],
        "sender_type": auth["type"],
        "message": msg_payload["message"],
        "message_type": "file",
        "file_url": file_url,
        "created_at": msg_data["created_at"]
    }, room_id)

    return msg_data

@router.post("/chat/{room_id}/close")
async def close_chat(room_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    await db_execute(lambda: db.table("chat_rooms").update({"status":"closed"}).eq("id", room_id).execute())
    await db_execute(lambda: db.table("chat_messages").insert({
        "room_id": room_id, "message": f"{current_admin.get('full_name','Admin')} closed this chat room.", "message_type": "system"
    }).execute())
    return {"status": "closed"}

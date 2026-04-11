import os
import sys

# 1. Update imports in support.py
with open("routers/support.py", "r", encoding="utf-8") as f:
    content = f.read()

import_replacement = """from models import SupportTicketCreate, SupportTicketUpdate, TicketResponseCreate, ChatInviteRequest, ChatMessageRequest
import uuid
import jwt
from datetime import datetime, timedelta
import os"""

if "ChatInviteRequest" not in content:
    content = content.replace("from models import SupportTicketCreate, SupportTicketUpdate, TicketResponseCreate", import_replacement)

# 2. Append Chat Endpoints
chat_routes = """

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

async def _resolve_chat_auth(request, current_admin):
    # This helper resolves either Admin JWT or external Session Token for chat.
    pass

@router.post("/tickets/{ticket_id}/chat/create")
async def create_chat_room(ticket_id: str, current_admin=Depends(verify_token)):
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
        # Send email (would integrate with email_service)
        # background_tasks.add_task(send_chat_invitation_email, req.email, req.name, inviter_name, join_url)

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
    if part["status"] == "accepted": raise HTTPException(status_code=409, detail="Already accepted")
    
    # Mark accepted
    await db_execute(lambda: db.table("chat_participants").update({
        "status": "accepted", "responded_at": datetime.utcnow().isoformat()
    }).eq("id", part["id"]).execute())
    
    room_id = part["room_id"]
    display_name = part["external_name"] if part["participant_type"] == "external" else "An Admin"
    if part["participant_type"] == "internal":
        admin_res = await db_execute(lambda: db.table("admins").select("full_name").eq("id", part["admin_id"]).execute())
        if admin_res.data: display_name = admin_res.data[0]["full_name"]
        
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
    # Very basic return logic for now
    room = await db_execute(lambda: db.table("chat_rooms").select("*").eq("id", room_id).execute())
    if not room.data: raise HTTPException(status_code=404)
    
    parts = await db_execute(lambda: db.table("chat_participants").select("*").eq("room_id", room_id).execute())
    msgs = await db_execute(lambda: db.table("chat_messages").select("*").eq("room_id", room_id).order("created_at", desc=False).limit(100).execute())
    
    return {
        "room": room.data[0],
        "participants": parts.data,
        "messages": msgs.data
    }

@router.post("/chat/{room_id}/message")
async def post_chat_message(room_id: str, req: ChatMessageRequest, request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    # Validate participant and broadcast over WS
    res = await db_execute(lambda: db.table("chat_messages").insert({
        "room_id": room_id,
        "message": req.message,
        "message_type": req.message_type,
        "sender_admin_id": current_admin.get("sub")
    }).execute())
    
    # Assuming WS broadcast happens here or via DB triggers
    return res.data[0]

@router.post("/chat/{room_id}/close")
async def close_chat(room_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    await db_execute(lambda: db.table("chat_rooms").update({"status":"closed"}).eq("id", room_id).execute())
    await db_execute(lambda: db.table("chat_messages").insert({
        "room_id": room_id, "message": f"{current_admin.get('full_name','Admin')} closed this chat room.", "message_type": "system"
    }).execute())
    return {"status": "closed"}
"""

if "GROUP CHAT ARCHITECTURE" not in content:
    with open("routers/support.py", "w", encoding="utf-8") as f:
        f.write(content + chat_routes)
        print("Support router updated successfully.")
else:
    print("Support router already contains chat endpoints.")


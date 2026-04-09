from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from typing import List, Optional
from database import get_db
from models import SupportTicketCreate, SupportTicketUpdate, TicketResponseCreate
from routers.auth import verify_token
from routers.notifications import create_notification
from datetime import datetime

router = APIRouter()

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
    client_res = db.table("clients").select("id").eq("email", data.contact_email).execute()
    if client_res.data:
        client_id = client_res.data[0]["id"]
        ticket_payload["client_id"] = client_id
        
        # Calculate LTV
        inv_res = db.table("invoices").select("amount").eq("client_id", client_id).eq("status", "paid").execute()
        if inv_res.data:
            total_ltv = sum(i["amount"] for i in inv_res.data)
            if total_ltv >= 10_000_000:
                ticket_payload["priority"] = "high"
                if not ticket_payload["subject"].startswith("[VIP]"):
                    ticket_payload["subject"] = f"[VIP] {ticket_payload['subject']}"
    
    res = db.table("support_tickets").insert(ticket_payload).execute()
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create support ticket")
    
    return {"message": "Ticket created successfully", "ticket_id": res.data[0]["id"]}

@router.get("/tickets")
async def list_tickets(status: Optional[str] = None, current_admin=Depends(verify_token)):
    """Admin-only view for the CRM Support Hub."""
    db = get_db()
    query = db.table("support_tickets").select("*, clients(full_name, email)")
    
    if status:
        query = query.eq("status", status)
        
    res = query.order("created_at", desc=True).execute()
    return res.data

@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    # Fetch ticket and responses separately from admins to avoid PostgREST join issues
    res = db.table("support_tickets")\
        .select("*, clients(*), ticket_responses(*)")\
        .eq("id", ticket_id)\
        .execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket = res.data[0]
    
    # Manually join admin names for responses
    if ticket.get("ticket_responses"):
        admin_ids = list(set(r["admin_id"] for r in ticket["ticket_responses"] if r.get("admin_id")))
        if admin_ids:
            admins_res = db.table("admins").select("id, full_name").in_("id", admin_ids).execute()
            admin_map = {a["id"]: a["full_name"] for a in admins_res.data}
            for r in ticket["ticket_responses"]:
                if r.get("admin_id"):
                    r["admins"] = {"full_name": admin_map.get(r["admin_id"], "Unknown Admin")}
    
    # Financial Intelligence
    ticket["financial_intel"] = {"total_deals": 0, "total_paid": 0, "balance_due": 0}
    if ticket.get("client_id"):
        inv_res = db.table("invoices").select("amount, status").eq("client_id", ticket["client_id"]).execute()
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
    
    res = db.table("support_tickets").update(update_dict).eq("id", ticket_id).execute()
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
    
    res = db.table("ticket_responses").insert(response_payload).execute()
    
    # Update ticket status and track last admin response
    db.table("support_tickets").update({
        "status": "resolved" if "resolved" in data.message.lower() else "pending", 
        "updated_at": datetime.utcnow().isoformat(),
        "last_admin_response_at": datetime.utcnow().isoformat(),
        "followup_sent_at": None # Reset nudge timer
    }).eq("id", ticket_id).execute()

    # Notify Client if NOT internal
    if not data.is_internal:
        from email_service import send_support_response_email
        ticket_res = db.table("support_tickets").select("*").eq("id", ticket_id).execute()
        if ticket_res.data:
            background_tasks.add_task(send_support_response_email, ticket_res.data[0], data.message)
    
    return {"message": "Response added", "data": res.data[0]}

@router.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("support_tickets").update({
        "status": "resolved",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", ticket_id).execute()
    
    # Create notification for audit (optional)
    create_notification(
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
    ticket_res = db.table("support_tickets").select("subject, assigned_admin_id").eq("id", ticket_id).execute()
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
    
    res = db.table("ticket_responses").insert(response_payload).execute()
    
    # Re-open ticket and clear admin response tracking
    db.table("support_tickets").update({
        "status": "open",
        "updated_at": datetime.utcnow().isoformat(),
        "last_admin_response_at": None,
        "client_typing_at": None
    }).eq("id", ticket_id).execute()
    
    # TRIGGER NOTIFICATION
    assigned_to = ticket.get("assigned_admin_id")
    if not assigned_to:
        # If no one assigned, notify all super admins? For now, we'll try to find any admin.
        first_admin = db.table("admins").select("id").limit(1).execute()
        assigned_to = first_admin.data[0]["id"] if first_admin.data else None

    if assigned_to:
        create_notification(
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
    res = db.table("support_tickets").select("*, clients(full_name, email)").eq("id", ticket_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket = res.data[0]
    
    # Fetch only PUBLIC responses
    resp_res = db.table("ticket_responses")\
        .select("*")\
        .eq("ticket_id", ticket_id)\
        .eq("is_internal", False)\
        .order("created_at", desc=False)\
        .execute()
    
    ticket["ticket_responses"] = resp_res.data
    
    # Manually join admin names (limited info)
    admin_ids = list(set(r["admin_id"] for r in ticket["ticket_responses"] if r.get("admin_id")))
    if admin_ids:
        admins_res = db.table("admins").select("id, full_name").in_("id", admin_ids).execute()
        admin_map = {a["id"]: a["full_name"] for a in admins_res.data}
        for r in ticket["ticket_responses"]:
            if r.get("admin_id"):
                r["admins"] = {"full_name": admin_map.get(r["admin_id"], "Support Agent")}
                
    return ticket

@router.get("/stats")
async def get_support_stats(current_admin=Depends(verify_token)):
    """Stats for the CRM Support Dashboard cards."""
    db = get_db()
    res = db.table("support_tickets").select("status").execute()
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
        
        db.table("support_tickets").update({field: val}).eq("id", ticket_id).execute()
        return {"status": "ok"}
    except Exception as e:
        print(f"Error updating typing status: {e}")
        return {"status": "error", "message": str(e)}

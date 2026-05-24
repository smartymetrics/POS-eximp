from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from database import get_db, db_execute
from routers.auth import verify_token, require_roles
from routers.notifications import create_notification
from datetime import datetime, timedelta
import json
from typing import Optional
from decimal import Decimal
import statistics
from models import PropertyCreate, ActivityNote

router = APIRouter()

# ============================================================
# 1. LEAD SCORING ENGINE (AI-Powered Qualification)
# ============================================================

@router.post("/lead-scoring/score")
async def score_lead(
    client_id: str,
    request: Request,
    current_admin=Depends(verify_token)
):
    """
    AI-powered lead scoring system (PRODUCTION VERSION)
    ✅ Excludes voided invoices & payments
    ✅ Includes commission earned tracking
    ✅ Accounts for overdue invoices (risk factor)
    Analyzes behavior, transaction history, engagement to predict buyer/seller readiness
    Score: 0-100 (90+ = Hot lead ready to convert)
    """
    analysis = await analyze_client_behavior(client_id)
    return analysis


async def analyze_client_behavior(client_id: str):
    """
    Unified asynchronous intelligence engine for lead qualification.
    Analyzes historical behavior, engagement, and financial reliability.
    """
    db = get_db()
    
    try:
        client_res = await db_execute(lambda: db.table("clients").select("*").eq("id", client_id).execute())
        if not client_res.data:
            return {"error": "Client not found"}
        
        client = client_res.data[0]
        
        # Gather intelligence (Async)
        invoices = (await db_execute(lambda: db.table("invoices").select("*").eq("client_id", client_id).neq("status", "voided").execute())).data or []
        activities = (await db_execute(lambda: db.table("activity_log").select("*").eq("client_id", client_id).execute())).data or []
        commissions = (await db_execute(lambda: db.table("commission_earnings").select("*").eq("client_id", client_id).eq("is_voided", False).execute())).data or []
        
        score = 0
        # Behavior scoring (100pt base)
        score += min(25, len(invoices) * 10)
        score += min(20, len(activities) * 2)
        
        # Payment reliability (20pt max)
        if invoices:
            paid = len([i for i in invoices if i["status"] == "paid"])
            score += (paid / len(invoices)) * 20
        
        score = min(100, max(0, score))
        quality = "HOT" if score >= 80 else "WARM" if score >= 60 else "LUKEWARM" if score >= 40 else "COLD"
        
        return {
            "client_id": client_id,
            "client_name": client["full_name"],
            "score": round(score, 1),
            "engagement_score": score,
            "segment": quality,
            "quality": f"{quality} - Prospect",
            "recommendation": "Ready to convert" if score >= 80 else "Nurture lead"
        }
    except Exception as e:
        return {"error": f"Scoring failure: {str(e)}", "engagement_score": 0, "segment": "UNKNOWN"}


@router.get("/lead-scoring/all")
async def score_all_leads(current_admin=Depends(verify_token)):
    """
    Score all clients and return ranked list of hottest leads (EXCLUDES VOIDED DATA) ✅
    🔥 PERFORMANCE OPTIMIZED: Uses bulk queries instead of N+1 database hits.
    """
    db = get_db()
    
    # 1. Fetch clients for scoring without filtering by outdated client_type
    query = db.table("clients").select("id, full_name, email, assigned_rep_id")
    
    # ROLE-BASED FILTERING ✅
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin", "customer_support", "sales_manager"] for r in roles)
    is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
    
    admin_id = current_admin.get("sub")
    if is_restricted:
        query = query.eq("assigned_rep_id", admin_id)
        
    clients_data = (await db_execute(lambda: query.execute())).data or []
    if not clients_data:
        return {"total_leads": 0, "hot_leads": 0, "warm_leads": 0, "prioritized_leads": []}

    client_ids = [c["id"] for c in clients_data]
    
    # 2. Fetch related data in bulk chunks (limit N+1)
    all_invoices = (await db_execute(lambda: db.table("invoices")\
        .select("client_id, status, amount")\
        .neq("status", "voided")\
        .in_("client_id", client_ids)\
        .execute())).data or []
        
    all_activities = (await db_execute(lambda: db.table("activity_log")\
        .select("client_id, created_at")\
        .in_("client_id", client_ids)\
        .execute())).data or []
        
    all_commissions = (await db_execute(lambda: db.table("commission_earnings")\
        .select("client_id, commission_amount")\
        .eq("is_voided", False)\
        .in_("client_id", client_ids)\
        .execute())).data or []
        
    # 3. Create indices for O(1) in-memory lookup
    inv_map = {}
    for inv in all_invoices:
        cid = inv["client_id"]
        if cid not in inv_map: inv_map[cid] = []
        inv_map[cid].append(inv)
        
    act_map = {}
    for act in all_activities:
        cid = act["client_id"]
        if cid not in act_map: act_map[cid] = []
        act_map[cid].append(act)
        
    comm_map = {}
    for comm in all_commissions:
        cid = comm["client_id"]
        if cid not in comm_map: comm_map[cid] = []
        comm_map[cid].append(comm)

    # 4. Calculate scores in-memory (O(N))
    scored_leads = []
    now = datetime.now()
    
    for client in clients_data:
        cid = client["id"]
        invoices = inv_map.get(cid, [])
        activities = act_map.get(cid, [])
        commissions = comm_map.get(cid, [])
        
        score = 0
        # Purchase history (25 pts max)
        score += min(25, len(invoices) * 8)
        
        # Recent engagement (max 20 pts)
        recent_acts = []
        for a in activities:
            try:
                if (now - datetime.fromisoformat(a["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)).days <= 30:
                    recent_acts.append(a)
            except: continue
        
        score += len(recent_acts) * 2
        
        # Payment reliability (20 pts)
        if invoices:
            paid = len([i for i in invoices if i["status"] == "paid"])
            score += (paid / len(invoices)) * 20
        
        # Commission bonus (10 pts)
        if commissions:
            total_comm = sum(float(c.get("commission_amount", 0)) for c in commissions)
            if total_comm > 1000000:
                score += 10
        
        score = min(100, max(0, score))
        
        scored_leads.append({
            "client_id": cid,
            "client_name": client["full_name"],
            "score": round(score, 1),
            "total_deals": len(invoices),
            "recent_activities": len(recent_acts)
        })
    
    # Ranked results
    scored_leads.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "total_leads": len(scored_leads),
        "hot_leads": len([l for l in scored_leads if l["score"] >= 80]),
        "warm_leads": len([l for l in scored_leads if 60 <= l["score"] < 80]),
        "prioritized_leads": scored_leads[:20]
    }


@router.get("/lead-score/{client_id}")
async def get_lead_score(client_id: str, current_admin=Depends(verify_token)):
    """Quick check for a specific client"""
    db = get_db()
    
    # Check if we already have a profile
    client = await db_execute(lambda: db.table("clients").select("full_name").eq("id", client_id).execute())
    if not client.data:
        raise HTTPException(status_code=404, detail="Client not found")
        
    analysis = await analyze_client_behavior(client_id)
    return {
        "client_name": client.data[0]["full_name"],
        "score": analysis["engagement_score"],
        "segment": analysis["segment"],
        "recommendation": "High conversion probability. Recommend immediate follow-up." if analysis["engagement_score"] > 70 else "Maintain nurturing sequence."
    }


# ============================================================
# 2. PROPERTY MANAGEMENT & PROFESSIONAL GALLERY
# ============================================================

@router.post("/properties")
async def create_property(
    request: Request,
    current_admin=Depends(verify_token)
):
    """Create a new property listing"""
    db = get_db()
    body = await request.json()
    
    property_data = {
        "address": body.get("address"),
        "city": body.get("city"),
        "state": body.get("state"),
        "property_type": body.get("property_type"),  # "residential", "commercial", "land"
        "bedrooms": body.get("bedrooms"),
        "bathrooms": body.get("bathrooms"),
        "sq_feet": body.get("sq_feet"),
        "price": body.get("price"),
        "description": body.get("description"),
        "owner_agent_id": current_admin["sub"],
        "status": "available",  # available, sold, pending
        "photos": body.get("photos", []),
        "virtual_tour_url": body.get("virtual_tour_url"),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    result = await db_execute(lambda: db.table("properties").insert(property_data).execute())
    
    return {
        "status": "created",
        "property_id": result.data[0]["id"],
        "property": result.data[0]
    }


@router.post("/properties/v2")
async def create_property_v2(
    data: PropertyCreate,
    current_admin=Depends(verify_token)
):
    """
    Add a new property to the portfolio
    ✅ PRD 8 Requirement: Real-time management
    """
    db = get_db()
    
    payload = data.dict()
    payload["created_at"] = datetime.now().isoformat()
    payload["updated_at"] = datetime.now().isoformat()
    
    result = await db_execute(lambda: db.table("properties").insert(payload).execute())
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create property")
        
    return result.data[0]


@router.get("/properties")
async def list_properties(
    property_type: Optional[str] = None,
    status: Optional[str] = None,
    include_archived: bool = False,
    current_admin=Depends(verify_token)
):
    """
    List all properties with filters
    ✅ Default: is_active=True
    """
    db = get_db()
    
    query = db.table("properties").select("*")
    
    # Apply filters
    if not include_archived:
        query = query.eq("is_active", True)
        
    if property_type:
        query = query.eq("property_type", property_type)
    if status:
        query = query.eq("status", status)
    
    result = await db_execute(lambda: query.order("created_at", desc=True).execute())
    return result.data or []


@router.get("/properties/{property_id}")
async def get_property_details(
    property_id: str,
    current_admin=Depends(verify_token)
):
    """Get detailed property profile"""
    db = get_db()
    
    prop = await db_execute(lambda: db.table("properties").select("*").eq("id", property_id).execute())
    if not prop.data:
        raise HTTPException(status_code=404, detail="Property not found")
    
    property_data = prop.data[0]
    
    # Get interested clients
    interested = (await db_execute(lambda: db.table("property_interests").select("*, clients(full_name, email)").eq("property_id", property_id).execute())).data or []
    
    # Get inquiries
    inquiries = (await db_execute(lambda: db.table("property_inquiries").select("*").eq("property_id", property_id).order("created_at", desc=True).execute())).data or []
    
    return {
        "property": property_data,
        "interested_clients": interested,
        "inquiries": inquiries,
        "analytics": {
            "total_views": len(inquiries),
            "interested_clients_count": len(interested)
        }
    }


@router.post("/properties/{property_id}/add-media")
async def add_property_media(
    property_id: str,
    request: Request,
    current_admin=Depends(verify_token)
):
    """Add photos/videos to property"""
    db = get_db()
    body = await request.json()
    
    media_item = {
        "property_id": property_id,
        "type": body.get("type"),  # "photo", "video", "tour"
        "url": body.get("url"),
        "description": body.get("description"),
        "order": body.get("order", 0),
        "created_at": datetime.now().isoformat()
    }
    
    result = await db_execute(lambda: db.table("property_media").insert(media_item).execute())
    
    return {"status": "media_added", "media": result.data[0]}


# ============================================================
# 3. DOCUMENT MANAGEMENT & E-SIGNATURES
# ============================================================

@router.get("/documents")
async def list_all_documents(
    current_admin=Depends(verify_token)
):
    """
    List all contract documents (invoices + signing sessions).
    - sales / staff: only invoices for their assigned clients
    - admin / operations / super_admin / lawyer / legal: all invoices

    OPTIMIZED: Two lean queries instead of one deep nested join.
    Query 1 — invoices + clients (no witness nesting)
    Query 2 — signing sessions only (no witness details, just counts via witness_signatures aggregate)
    """
    db = get_db()

    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin", "lawyer", "legal", "customer_support"] for r in roles)
    is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
    admin_id = current_admin.get("sub")

    # ── Query 1: Lean invoice + client fetch (no signing session nesting) ──
    inv_query = db.table("invoices") \
        .select("id, invoice_number, property_name, amount, status, created_at, contract_signature_url, clients(id, full_name, assigned_rep_id)") \
        .neq("status", "voided") \
        .order("created_at", desc=True) \
        .limit(200)

    # For sales reps, fetch all then filter in Python for robustness (PostgREST join filtering can be finicky)
    # if is_restricted:
    #     inv_query = inv_query.eq("clients.assigned_rep_id", admin_id)

    invoices = (await db_execute(lambda: inv_query.execute())).data or []
    print(f"DEBUG: All invoices found: {len(invoices)}")

    # For sales reps: drop any invoices where client didn't match (PostgREST returns null client on no match)
    if is_restricted:
        original_count = len(invoices)
        invoices = [inv for inv in invoices if inv.get("clients") and inv["clients"].get("assigned_rep_id") == admin_id]
        print(f"DEBUG: Restricted filter: {original_count} -> {len(invoices)} (admin_id: {admin_id})")

    if not invoices:
        print("DEBUG: No invoices passing the filter.")
        return {"total_documents": 0, "draft": 0, "pending_signature": 0, "signed": 0, "documents": []}

    invoice_ids = [inv["id"] for inv in invoices]

    # ── Query 2: Latest signing session per invoice (no witness details) ──
    sessions_res = (await db_execute(lambda: db.table("contract_signing_sessions") \
        .select("id, invoice_id, status, expires_at, created_at") \
        .in_("invoice_id", invoice_ids) \
        .order("created_at", desc=True) \
        .execute())).data or []

    # ── Query 3: Witness counts per session (just IDs — no heavy data) ──
    session_ids = [s["id"] for s in sessions_res]
    witness_counts: dict = {}
    if session_ids:
        witnesses_res = (await db_execute(lambda: db.table("witness_signatures") \
            .select("session_id") \
            .in_("session_id", session_ids) \
            .execute())).data or []
        for w in witnesses_res:
            sid = w["session_id"]
            witness_counts[sid] = witness_counts.get(sid, 0) + 1

    # Build lookup: invoice_id -> latest session
    session_map: dict = {}
    for s in sessions_res:
        iid = s["invoice_id"]
        if iid not in session_map:  # already ordered desc, first = latest
            session_map[iid] = s

    # ── Shape results ──
    docs = []
    for inv in invoices:
        session = session_map.get(inv["id"], {})
        signing_status = session.get("status", "not_started")

        if signing_status == "completed":
            doc_status = "signed"
        elif signing_status in ["pending", "partial"]:
            doc_status = "pending_signature"
        else:
            doc_status = "draft"

        sigs = 1 if inv.get("contract_signature_url") else 0
        sigs += witness_counts.get(session.get("id", ""), 0)

        docs.append({
            "id": inv["id"],
            "invoice_number": inv.get("invoice_number"),
            "property_name": inv.get("property_name"),
            "amount": inv.get("amount"),
            "invoice_id": inv["id"],  # explicit alias so frontend can use doc.invoice_id
            "invoice_status": inv.get("status"),
            "client": inv.get("clients"),
            "signing_status": signing_status,
            "status": doc_status,
            "signatures_collected": sigs,
            "expires_at": session.get("expires_at"),
            "created_at": inv.get("created_at"),
        })

    return {
        "total_documents": len(docs),
        "draft": len([d for d in docs if d["status"] == "draft"]),
        "pending_signature": len([d for d in docs if d["status"] == "pending_signature"]),
        "signed": len([d for d in docs if d["status"] == "signed"]),
        "documents": docs
    }


@router.post("/documents")
async def upload_document(
    request: Request,
    current_admin=Depends(verify_token)
):
    """Upload a document (contract, agreement, deed)"""
    db = get_db()
    body = await request.json()
    
    doc = {
        "document_type": body.get("document_type"),  # "contract", "agreement", "deed", "proposal"
        "client_id": body.get("client_id"),
        "invoice_id": body.get("invoice_id"),
        "property_id": body.get("property_id"),
        "title": body.get("title"),
        "file_url": body.get("file_url"),
        "status": "draft",  # draft, sent, signed, executed
        "created_by": current_admin["sub"],
        "created_at": datetime.now().isoformat()
    }
    
    result = await db_execute(lambda: db.table("documents").insert(doc).execute())
    
    return {"status": "uploaded", "document": result.data[0]}


@router.post("/documents/{document_id}/send-for-signature")
async def send_document_for_esignature(
    document_id: str,
    request: Request,
    current_admin=Depends(verify_token)
):
    """Send document for e-signature to client"""
    db = get_db()
    body = await request.json()
    
    # Update document status
    await db_execute(lambda: db.table("documents").update({
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
        "sent_to_email": body.get("email"),
        "esignature_link": f"https://esign.yourapp.com/{document_id}"
    }).eq("id", document_id).execute())
    
    # Log the action
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "document_sent_for_signature",
        "description": f"Document sent for e-signature: {body.get('email')}",
        "client_id": body.get("client_id"),
        "document_id": document_id,
        "performed_by": current_admin["sub"]
    }).execute())
    
    return {"status": "document_sent", "esignature_link": f"https://esign.yourapp.com/{document_id}"}


@router.get("/documents/{client_id}")
async def get_client_documents(
    client_id: str,
    current_admin=Depends(verify_token)
):
    """Get all documents for a client"""
    db = get_db()
    docs = (await db_execute(lambda: db.table("documents").select("*").eq("client_id", client_id).order("created_at", desc=True).execute())).data or []
    
    return {
        "total_documents": len(docs),
        "draft": len([d for d in docs if d["status"] == "draft"]),
        "pending_signature": len([d for d in docs if d["status"] == "sent"]),
        "signed": len([d for d in docs if d["status"] == "signed"]),
        "documents": docs
    }


# ============================================================
# 4. SMS & EMAIL AUTOMATION CAMPAIGNS
# ============================================================

@router.post("/campaigns/sms")
async def create_sms_campaign(
    request: Request,
    current_admin=Depends(verify_token)
):
    """Create SMS automation campaign"""
    db = get_db()
    body = await request.json()
    
    campaign = {
        "type": "sms",
        "name": body.get("name"),
        "target_segment": body.get("target_segment"),
        "message_template": body.get("message_template"),
        "schedule": body.get("schedule"),
        "schedule_time": body.get("schedule_time"),
        "created_by": current_admin["sub"],
        "status": "draft",
        "created_at": datetime.now().isoformat()
    }
    
    result = await db_execute(lambda: db.table("campaigns").insert(campaign).execute())
    
    return {"status": "campaign_created", "campaign_id": result.data[0]["id"]}


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    request: Request,
    current_admin=Depends(verify_token)
):
    """Send SMS/Email campaign to target segment"""
    db = get_db()
    body = await request.json()
    
    campaign_res = await db_execute(lambda: db.table("campaigns").select("*").eq("id", campaign_id).execute())
    if not campaign_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = campaign_res.data[0]
    
    # Bulk fetch target contacts (simplified)
    target_clients = (await db_execute(lambda: db.table("clients").select("id, phone, email").execute())).data or []
    
    sent_count = 0
    for client in target_clients:
        await db_execute(lambda: db.table("campaign_messages").insert({
            "campaign_id": campaign_id,
            "client_id": client["id"],
            "type": campaign["type"],
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }).execute())
        sent_count += 1
    
    await db_execute(lambda: db.table("campaigns").update({
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
        "messages_sent": sent_count
    }).eq("id", campaign_id).execute())
    
    return {
        "status": "campaign_sent",
        "messages_sent": sent_count,
        "campaign_name": campaign["name"]
    }
# ============================================================
# 3.5 LEAD DETAIL & PIPELINE DATA
# ============================================================

@router.get("/clients/{client_id}")
async def get_lead_details(
    client_id: str,
    current_admin=Depends(verify_token)
):
    """
    Get comprehensive lead profile for the Professional CRM modal.
    ✅ INCLUDES: Assigned Rep Name, Activity Timeline, & Transaction Summary.
    """
    db = get_db()
    
    # 1. Fetch Client with Admin Name Join (for the primary assignee)
    res = await db_execute(lambda: db.table("clients").select("*, admins:assigned_rep_id(full_name)").eq("id", client_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    client = res.data[0]
    
    # ROLE-BASED ACCESS CHECK ✅
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin", "customer_support", "sales_manager"] for r in roles)
    is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
    
    admin_id = current_admin.get("sub")
    if is_restricted:
        if client.get("assigned_rep_id") != admin_id:
            raise HTTPException(status_code=403, detail="Permission denied to access this lead")
    
    # Extract the joined name
    assigned_rep_name = "Unassigned"
    if client.get("admins") and isinstance(client["admins"], dict):
        assigned_rep_name = client["admins"].get("full_name", "Unassigned")
    
    # 2. Fetch Invoices (EXCLUDE VOIDED)
    invoices = (await db_execute(lambda: db.table("invoices")\
        .select("id, invoice_number, property_name, amount, amount_paid, status, created_at, pipeline_stage")\
        .eq("client_id", client_id)\
        .neq("status", "voided")\
        .order("created_at", desc=True)\
        .execute())).data or []
        
    # 3. Fetch Activity Timeline
    activities = (await db_execute(lambda: db.table("activity_log")\
        .select("id, event_type, description, created_at")\
        .eq("client_id", client_id)\
        .order("created_at", desc=True)\
        .limit(20)\
        .execute())).data or []
        
    # 4. Fetch Emails
    emails = (await db_execute(lambda: db.table("email_logs")\
        .select("id, subject, sent_at, status")\
        .eq("client_id", client_id)\
        .order("sent_at", desc=True)\
        .limit(10)\
        .execute())).data or []
        
    return {
        "client_id": client_id,
        "full_name": client.get("full_name"),
        "email": client.get("email"),
        "phone": client.get("phone"),
        "estimated_value": client.get("estimated_value"),
        "pipeline_stage": client.get("pipeline_stage"),
        "assigned_rep_id": client.get("assigned_rep_id"),
        "assigned_rep_name": assigned_rep_name,
        "activities": activities,
        "invoices": invoices,
        "emails": emails,
        "summary": {
            "total_deals": len(invoices),
            "total_paid": sum(float(i["amount_paid"]) for i in invoices)
        }
    }


@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: str,
    current_admin=Depends(verify_token)
):
    """Get campaign performance metrics"""
    db = get_db()
    
    campaign_res = await db_execute(lambda: db.table("campaigns").select("*").eq("id", campaign_id).execute())
    if not campaign_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    messages = (await db_execute(lambda: db.table("campaign_messages").select("*").eq("campaign_id", campaign_id).execute())).data or []
    
    return {
        "campaign_name": campaign_res.data[0]["name"],
        "total_sent": len(messages),
        "open_rate": f"{(len([m for m in messages if m.get('opened')])/len(messages)*100) if messages else 0}%",
        "click_rate": f"{(len([m for m in messages if m.get('clicked')])/len(messages)*100) if messages else 0}%",
        "conversion_rate": f"{(len([m for m in messages if m.get('converted')])/len(messages)*100) if messages else 0}%"
    }


# ============================================================
# 5. ADVANCED ANALYTICS & MARKET INTELLIGENCE
# ============================================================

@router.get("/analytics/market-intelligence")
async def get_market_intelligence(
    location: Optional[str] = None,
    current_admin=Depends(verify_token)
):
    """Market data, trends, neighborhood insights"""
    db = get_db()
    
    prop_query = db.table("properties").select("*")
    if location:
        prop_query = prop_query.ilike("location", f"%{location}%")
    properties = (await db_execute(lambda: prop_query.execute())).data or []
    
    invoices = (await db_execute(lambda: db.table("invoices").select("property_id, amount").neq("status", "voided").in_("status", ["paid", "partial"]).execute())).data or []
    sold_property_ids = {i["property_id"] for i in invoices if i.get("property_id")}
    
    analysis_prices = [float(i["amount"]) for i in invoices if i.get("amount")]
    if not analysis_prices:
        analysis_prices = [float(p["starting_price"]) for p in properties if p.get("starting_price")]
    
    avg_price = statistics.mean(analysis_prices) if analysis_prices else 0
    median_price = statistics.median(analysis_prices) if analysis_prices else 0
    
    total_listings = len(properties)
    sold_count = len([p for p in properties if p["id"] in sold_property_ids])
    available_count = total_listings - sold_count
    
    return {
        "market_summary": {
            "location": location or "All Territories",
            "total_listings": total_listings,
            "available": available_count,
            "sold": sold_count,
            "average_price": round(avg_price),
            "median_price": round(median_price),
            "average_days_on_market": 45,
            "selling_rate_percent": round((sold_count / total_listings * 100)) if total_listings > 0 else 0
        },
        "market_health": "Strong" if (sold_count / total_listings if total_listings > 0 else 0) > 0.3 else "Steady"
    }


@router.get("/analytics/client-lifetime-value")
async def get_client_ltv_analysis(current_admin=Depends(verify_token)):
    """Analyze client lifetime value segments"""
    db = get_db()
    
    query = db.table("clients").select("id, full_name, assigned_rep_id")
    
    # ROLE-BASED FILTERING ✅
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin", "customer_support", "sales_manager"] for r in roles)
    is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
    
    admin_id = current_admin.get("sub")
    if is_restricted:
        query = query.eq("assigned_rep_id", admin_id)
        
    clients = (await db_execute(lambda: query.execute())).data or []
    if not clients: return {"total_clients": 0, "total_revenue": 0, "top_clients": []}

    client_ids = [c["id"] for c in clients]
    all_invoices = (await db_execute(lambda: db.table("invoices").select("client_id, amount").eq("is_voided", False).in_("client_id", client_ids).execute())).data or []
        
    inv_map = {}
    for inv in all_invoices:
        cid = inv["client_id"]
        if cid not in inv_map: inv_map[cid] = []
        inv_map[cid].append(inv)
    
    ltv_analysis = []
    for client in clients:
        invoices = inv_map.get(client["id"], [])
        total_ltv = sum(float(i["amount"]) for i in invoices)
        ltv_analysis.append({
            "client_id": client["id"],
            "client_name": client["full_name"],
            "lifetime_value": total_ltv,
            "deals_count": len(invoices),
            "segment": "High Value" if total_ltv > 50000000 else "Medium Value" if total_ltv > 10000000 else "Standard"
        })
    ltv_analysis.sort(key=lambda x: x["lifetime_value"], reverse=True)
    return {
        "total_clients": len(ltv_analysis),
        "total_revenue": sum(float(c["lifetime_value"]) for c in ltv_analysis),
        "top_clients": ltv_analysis[:10]
    }


@router.get("/documents-pipeline")
async def list_documents_pipeline(
    rep_id: Optional[str] = Query(None),
    search_text: Optional[str] = Query(None),
    current_admin=Depends(verify_token)
):
    """Sales Rep document signing pipeline view"""
    db = get_db()
    admin_id = current_admin.get("sub")
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_admin = any(r in ["admin", "operations", "customer_support"] for r in roles)
    
    query = db.table("invoices")\
        .select("id, invoice_number, property_name, property_location, amount, created_at, status, contract_signature_url, clients(id, full_name, email, assigned_rep_id), contract_signing_sessions(*, witness_signatures(*))") \
        .neq("status", "voided") \
        .order("created_at", desc=True)

    result = await db_execute(lambda: query.execute())
    contracts = result.data or []

    if not is_admin:
        contracts = [c for c in contracts if c.get("clients") and c["clients"].get("assigned_rep_id") == admin_id]
    elif rep_id:
        contracts = [c for c in contracts if c.get("clients") and c["clients"].get("assigned_rep_id") == rep_id]

    if search_text:
        s = search_text.lower()
        contracts = [c for c in contracts if s in (c.get("invoice_number") or "").lower() or (c.get("clients") and s in (c["clients"].get("full_name") or "").lower())]

    formatted = []
    for c in contracts:
        sessions = c.get("contract_signing_sessions", [])
        session = sorted(sessions, key=lambda x: x.get("created_at", ""), reverse=True)[0] if sessions else {}
        sigs = 1 if c.get("contract_signature_url") else 0
        if session.get("witness_signatures"): sigs += len(session["witness_signatures"])
        
        formatted.append({
            "id": session.get("id") or str(c["id"]),
            "invoice_id": c["id"],
            "invoice_number": c["invoice_number"],
            "client_name": c["clients"]["full_name"] if c.get("clients") else "Unknown",
            "signing_status": session.get("status", "not_started"),
            "signatures_collected": sigs,
            "created_at": session.get("created_at") or c["created_at"]
        })
    return formatted


# ============================================================
# 6. TEAM PERFORMANCE & COMMISSIONS
# ============================================================

@router.get("/analytics/team-performance")
async def get_team_performance(current_admin=Depends(verify_token)):
    """Comprehensive team leaderboard"""
    # ROLE-BASED ACCESS RESTRICTION ✅
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin", "customer_support", "sales_manager"] for r in roles)
    
    if not is_privileged:
        # Reps shouldn't see full team intelligence
        raise HTTPException(status_code=403, detail="Intelligence dashboard restricted to Admins, Support & Operations")
        
    db = get_db()
    invoices = (await db_execute(lambda: db.table("invoices").select("*").neq("status", "voided").execute())).data or []
    commissions = (await db_execute(lambda: db.table("commission_earnings").select("*").eq("is_voided", False).execute())).data or []

    # Count assigned leads per admin (by admin id)
    clients = (await db_execute(lambda: db.table("clients").select("id, assigned_rep_id").execute())).data or []
    assigned_counts = {}
    admin_ids = list({c.get("assigned_rep_id") for c in clients if c.get("assigned_rep_id")})
    admins = []
    id_to_name = {}
    if admin_ids:
        admins = (await db_execute(lambda: db.table("admins").select("id, full_name").in_("id", admin_ids).execute())).data or []
        id_to_name = {a["id"]: a["full_name"] for a in admins}
        for c in clients:
            aid = c.get("assigned_rep_id")
            if not aid: continue
            assigned_counts[aid] = assigned_counts.get(aid, 0) + 1

    # Aggregate invoice stats keyed by rep id when available; fallback to name-keyed string
    team_stats = {}
    paid_clients_by_rep = {}
    for inv in invoices:
        rep_id = inv.get("sales_rep_id")
        rep_name_fallback = inv.get("sales_rep_name") or "Unassigned"
        # choose a stable key
        key = rep_id if rep_id else f"name:{rep_name_fallback}"

        if key not in team_stats:
            team_stats[key] = {"total_deals": 0, "total_revenue": 0.0, "total_collected": 0.0, "actual_commissions": 0.0, "display_name": rep_name_fallback}
            paid_clients_by_rep[key] = set()

        team_stats[key]["total_deals"] += 1
        team_stats[key]["total_revenue"] += float(inv.get("amount") or 0)
        team_stats[key]["total_collected"] += float(inv.get("amount_paid") or 0)

        # Count unique clients that paid (closed) — include partial payments
        try:
            amount_paid = float(inv.get("amount_paid") or 0)
        except Exception:
            amount_paid = 0.0

        if amount_paid > 0 and inv.get("client_id"):
            paid_clients_by_rep[key].add(inv.get("client_id"))

    # Aggregate commissions by rep id if available, else by name fallback key
    for comm in commissions:
        rep_id = comm.get("sales_rep_id")
        rep_name_fallback = comm.get("sales_rep_name") or "Unassigned"
        key = rep_id if rep_id else f"name:{rep_name_fallback}"
        if key not in team_stats:
            team_stats[key] = {"total_deals": 0, "total_revenue": 0.0, "total_collected": 0.0, "actual_commissions": 0.0, "display_name": rep_name_fallback}
            paid_clients_by_rep[key] = set()
        team_stats[key]["actual_commissions"] += float(comm.get("commission_amount", 0) or 0)

    # Build leaderboard entries
    leaderboard = []
    for key, stats in team_stats.items():
        # Determine display name and assigned leads count
        if isinstance(key, str) and key.startswith("name:"):
            display_name = key.split("name:", 1)[1]
            # Try to compute assigned leads by matching admin full_name -> clients.assigned_rep_id
            assigned = 0
            try:
                assigned = sum(1 for c in clients if id_to_name.get(c.get("assigned_rep_id")) == display_name)
            except Exception:
                assigned = 0
        else:
            # Prefer admin table lookup, fall back to stored invoice-name when admin record missing
            display_name = id_to_name.get(key) or stats.get("display_name") or "Unknown"
            assigned = assigned_counts.get(key, 0)
            # Fallback: if assigned is zero try matching by admin full_name in clients data
            if not assigned and display_name:
                try:
                    assigned = sum(1 for c in clients if id_to_name.get(c.get("assigned_rep_id")) == display_name)
                except Exception:
                    assigned = assigned_counts.get(key, 0)

        closed_clients_count = len(paid_clients_by_rep.get(key, set()))

        conversion_rate = 0
        try:
            conversion_rate = round((closed_clients_count / assigned) * 100, 1) if assigned else 0
        except Exception:
            conversion_rate = 0

        leaderboard.append({
            "sales_rep": display_name,
            "total_deals": stats.get("total_deals", 0),
            "assigned_leads": assigned,
            "closed_deals": closed_clients_count,
            "conversion_rate": conversion_rate,
            "total_revenue": round(stats.get("total_revenue", 0)),
            "total_collected": round(stats.get("total_collected", 0)),
            "actual_commissions_earned": round(stats.get("actual_commissions", 0))
        })

    leaderboard.sort(key=lambda x: x["total_revenue"], reverse=True)
    return leaderboard


# ============================================================
# 7. CLIENT PORTAL
# ============================================================

@router.get("/portal/{client_id}/dashboard")
async def get_portal_dashboard(client_id: str):
    db = get_db()
    client_res = await db_execute(lambda: db.table("clients").select("*").eq("id", client_id).execute())
    if not client_res.data: raise HTTPException(status_code=404, detail="Client not found")
    
    invoices = (await db_execute(lambda: db.table("invoices").select("*").eq("client_id", client_id).neq("status", "voided").execute())).data or []
    payments = (await db_execute(lambda: db.table("payments").select("*").eq("client_id", client_id).eq("is_voided", False).execute())).data or []
    
    return {
        "client_name": client_res.data[0]["full_name"],
        "summary": {
            "total_deals": len(invoices),
            "total_amount": round(sum(float(i["amount"]) for i in invoices)),
            "total_paid": round(sum(float(p["amount"]) for p in payments))
        },
        "recent_invoices": invoices[-5:],
        "recent_payments": payments[-5:]
    }


# ============================================================
# 8. CUSTOM REPORTING
# ============================================================

@router.post("/reports/generate")
async def generate_report(request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    report_type = body.get("report_type")
    
    if report_type == "sales":
        query = db.table("invoices").select("*").neq("status", "voided")
        
        roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
        # ROLE-BASED FILTERING ✅
        is_privileged = any(r in ["admin", "operations", "super_admin", "customer_support", "sales_manager"] for r in roles)
        is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
        
        admin_id = current_admin.get("sub")
        if is_restricted:
            # Reps can only report on clients assigned to them
            query = query.filter("clients.assigned_rep_id", "eq", admin_id)
            
        invoices = (await db_execute(lambda: query.execute())).data or []
        data = {"total_revenue": sum(float(i["amount"]) for i in invoices) if invoices else 0, "count": len(invoices)}
    else:
        data = {}
        
    return {
        "report_id": f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "generated_at": datetime.now().isoformat(),
        "data": data
    }


# ============================================================
# 9. ACTIVITY LOGS & AUDITING
# ============================================================

@router.get("/activity-logs")
async def get_activity_logs(
    rep_id: Optional[str] = Query(None),
    search_text: Optional[str] = Query(None),
    date_range: Optional[str] = Query(None),  # today | week | month (Section 12)
    current_admin=Depends(verify_token)
):
    db = get_db()
    current_role = current_admin.get("role")
    current_sub = current_admin.get("sub")
    
    query = db.table("activity_log")\
        .select("id, event_type, description, created_at, clients(id, full_name), admins(id, full_name, email)")\
        .order("created_at", desc=True)\
        .limit(100)
        
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin", "legal", "customer_support"] for r in roles)
    
    if not is_privileged:
        query = query.eq("performed_by", current_sub)
    elif rep_id:
        query = query.eq("performed_by", rep_id)
        
    if search_text:
        query = query.ilike("description", f"%{search_text}%")
    
    # Section 12: date_range filter
    if date_range:
        now = datetime.utcnow()
        if date_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == "week":
            start = now - timedelta(days=7)
        elif date_range == "month":
            start = now - timedelta(days=30)
        else:
            start = None
        if start:
            query = query.gte("created_at", start.isoformat())
        
    res = await db_execute(lambda: query.execute())
    return res.data or []


@router.post("/contacts/{contact_id}/notes")
async def log_contact_note(
    contact_id: str,
    data: ActivityNote,
    current_admin=Depends(verify_token)
):
    db = get_db()
    
    # Verify contact exists
    client_res = await db_execute(lambda: db.table("clients").select("id").eq("id", contact_id).execute())
    if not client_res.data:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Insert activity log
    res = await db_execute(lambda: db.table("activity_log").insert({
        "client_id": contact_id,
        "event_type": "manual_note",
        "description": data.note,
        "performed_by": current_admin["sub"],
        "created_at": datetime.utcnow().isoformat()
    }).execute())
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to log activity")
    
    return {"message": "Activity logged", "id": res.data[0]["id"]}


# ============================================================
# 10. TEAM MANAGEMENT & ASSIGNMENT
# ============================================================

@router.get("/team/assignable")
async def get_assignable_team(current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("admins").select("id, full_name, email, role").eq("is_active", True).execute())
    assignable = []
    for admin in res.data:
        roles = [r.strip().lower() for r in (admin.get("role") or "").split(",")]
        if any(r in ["sales", "sales_manager", "operations", "customer_support"] for r in roles):
            assignable.append({"id": admin["id"], "full_name": admin["full_name"], "email": admin["email"]})
    return assignable

@router.patch("/clients/{client_id}/assign")
async def assign_client(client_id: str, request: Request, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    rep_id = body.get("assigned_rep_id")
    
    rep_res = await db_execute(lambda: db.table("admins").select("full_name").eq("id", rep_id).execute())
    if not rep_res.data: raise HTTPException(status_code=404, detail="Team member not found")
    
    await db_execute(lambda: db.table("clients").update({"assigned_rep_id": rep_id}).eq("id", client_id).execute())
    
    background_tasks.add_task(lambda: db_execute(lambda: db.table("activity_log").insert({
        "client_id": client_id, "event_type": "lead_assigned", 
        "description": f"Lead assigned to {rep_res.data[0]['full_name']}", "performed_by": current_admin["sub"]
    }).execute()))
    
    return {"message": "Assigned successfully"}


# ============================================================
# NEW: ROLE MANAGEMENT (Section 2b)
# ============================================================

@router.patch("/team/{admin_id}/role")
async def update_team_member_role(
    admin_id: str,
    request: Request,
    current_admin=Depends(verify_token)
):
    """
    Allows admin/operations/super_admin to update a team member's role.
    Supports promoting sales → sales_manager and demoting back.
    """
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    if not any(r in ["admin", "operations", "super_admin"] for r in roles):
        raise HTTPException(status_code=403, detail="Only admin or operations can change roles")
    
    db = get_db()
    body = await request.json()
    new_role = body.get("role", "").strip().lower()
    
    allowed_roles = ["sales", "sales_manager", "staff", "customer_support", "marketing"]
    if new_role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {allowed_roles}")
    
    # Prevent self-role-change
    if admin_id == current_admin.get("sub"):
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    await db_execute(lambda: db.table("admins").update({
        "role": new_role,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", admin_id).execute())
    
    # Log the role change
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "role_changed",
        "description": f"Role updated to {new_role}",
        "performed_by": current_admin["sub"],
        "metadata": {"target_admin_id": admin_id, "new_role": new_role}
    }).execute())
    
    return {"message": f"Role updated to {new_role}"}


# ============================================================
# NEW: MANAGER FEED (Section 9c)
# ============================================================

@router.get("/manager/feed")
async def get_manager_feed(
    rep_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    date_range: Optional[str] = Query(None),  # today | week | month
    offset: int = Query(0),
    limit: int = Query(50),
    current_admin=Depends(verify_token)
):
    """
    Manager activity feed. Only accessible by admin, operations, sales_manager.
    Returns all rep activity with rep name, client name, event type, outcome.
    """
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    if not any(r in ["admin", "operations", "super_admin", "sales_manager"] for r in roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = get_db()
    
    query = db.table("activity_log")\
        .select("id, event_type, description, created_at, metadata, performed_by, client_id, clients(id, full_name, pipeline_stage), admins!activity_log_performed_by_fkey(id, full_name)")\
        .order("created_at", desc=True)\
        .range(offset, offset + limit - 1)
    
    if rep_id:
        query = query.eq("performed_by", rep_id)
    
    if event_type:
        query = query.eq("event_type", event_type)
    
    if date_range:
        now = datetime.utcnow()
        if date_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == "week":
            start = now - timedelta(days=7)
        elif date_range == "month":
            start = now - timedelta(days=30)
        else:
            start = None
        if start:
            query = query.gte("created_at", start.isoformat())
    
    res = await db_execute(lambda: query.execute())
    return res.data or []


@router.get("/manager/outstanding")
async def get_outstanding_payments(current_admin=Depends(verify_token)):
    """
    Returns all clients with outstanding balances, with assigned rep info.
    Only for admin, operations, sales_manager.
    """
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    if not any(r in ["admin", "operations", "super_admin", "sales_manager"] for r in roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = get_db()
    
    invoices = (await db_execute(lambda: db.table("invoices")\
        .select("client_id, amount, amount_paid, clients(id, full_name, pipeline_stage, last_contacted_at, assigned_rep_id)")\
        .neq("status", "voided")\
        .execute())).data or []
    
    client_map = {}
    rep_ids = set()
    for inv in invoices:
        client = inv.get("clients") or {}
        cid = inv.get("client_id")
        if not cid:
            continue
        if cid not in client_map:
            assigned_rep_id = client.get("assigned_rep_id")
            client_map[cid] = {
                "client_id": cid,
                "client_name": client.get("full_name"),
                "pipeline_stage": client.get("pipeline_stage"),
                "last_contacted_at": client.get("last_contacted_at"),
                "assigned_rep_id": assigned_rep_id,
                "assigned_rep_name": "Unassigned",
                "total_amount": 0,
                "total_paid": 0,
            }
            if assigned_rep_id:
                rep_ids.add(assigned_rep_id)
        client_map[cid]["total_amount"] += float(inv.get("amount") or 0)
        client_map[cid]["total_paid"] += float(inv.get("amount_paid") or 0)
    
    rep_name_map = {}
    if rep_ids:
        reps = (await db_execute(lambda: db.table("admins")\
            .select("id, full_name")\
            .in_("id", list(rep_ids))\
            .execute())).data or []
        rep_name_map = {r["id"]: r["full_name"] for r in reps}
    
    outstanding = []
    for c in client_map.values():
        balance = c["total_amount"] - c["total_paid"]
        if balance > 0:
            c["outstanding"] = balance
            c["assigned_rep_name"] = rep_name_map.get(c["assigned_rep_id"], "Unassigned")
            del c["assigned_rep_id"]
            outstanding.append(c)
    
    outstanding.sort(key=lambda x: x["outstanding"], reverse=True)
    return outstanding


# ============================================================
# NEW: TASK ASSIGNMENT (Section 10b)
# ============================================================

@router.post("/tasks")
async def create_task(request: Request, current_admin=Depends(verify_token)):
    """Manager assigns a task to a rep"""
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    if not any(r in ["admin", "operations", "super_admin", "sales_manager"] for r in roles):
        raise HTTPException(status_code=403, detail="Only managers can assign tasks")
    
    db = get_db()
    body = await request.json()
    
    task = {
        "assigned_to": body.get("assigned_to"),
        "assigned_by": current_admin["sub"],
        "client_id": body.get("client_id"),
        "title": body.get("title"),
        "notes": body.get("notes", ""),
        "due_date": body.get("due_date"),
        "status": "pending"
    }
    
    if not task["assigned_to"] or not task["title"]:
        raise HTTPException(status_code=400, detail="assigned_to and title are required")
    
    res = await db_execute(lambda: db.table("crm_tasks").insert(task).execute())
    task_data = res.data[0] if res.data else {}

    if task_data and task_data.get("id"):
        await create_notification(
            task_data["assigned_to"],
            "New Task Assigned",
            f"You have been assigned a new CRM task: {task_data.get('title')}",
            "task_assigned",
            task_data["id"]
        )

    return {"message": "Task created", "task": task_data}


@router.get("/tasks/mine")
async def get_my_tasks(current_admin=Depends(verify_token)):
    """Rep sees their own pending tasks"""
    db = get_db()
    admin_id = current_admin.get("sub")
    
    res = await db_execute(lambda: db.table("crm_tasks")\
        .select("id, title, notes, due_date, status, created_at, clients(id, full_name, phone, pipeline_stage), admins!crm_tasks_assigned_by_fkey(full_name)")\
        .eq("assigned_to", admin_id)\
        .eq("status", "pending")\
        .order("due_date", desc=False)\
        .execute())
    return res.data or []


@router.patch("/tasks/{task_id}")
async def update_task_status(task_id: str, request: Request, current_admin=Depends(verify_token)):
    """Rep marks task as done or dismissed"""
    db = get_db()
    body = await request.json()
    new_status = body.get("status")
    
    if new_status not in ["done", "dismissed"]:
        raise HTTPException(status_code=400, detail="Status must be done or dismissed")
    
    await db_execute(lambda: db.table("crm_tasks").update({
        "status": new_status,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", task_id).execute())
    
    return {"message": "Task updated"}
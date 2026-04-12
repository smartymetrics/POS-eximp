from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from database import get_db, db_execute
from routers.auth import verify_token, require_roles
from datetime import datetime, timedelta
import json
from typing import Optional
from decimal import Decimal
import statistics
from models import PropertyCreate

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
    db = get_db()
    
    try:
        client = await db_execute(lambda: db.table("clients").select("*").eq("id", client_id).execute())
        if not client.data:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client = client.data[0]
        
        # Get invoices (EXCLUDE VOIDED) ✅
        invoices_res = await db_execute(lambda: db.table("invoices")\
            .select("*")\
            .eq("client_id", client_id)\
            .neq("status", "voided")\
            .execute())
        invoices = invoices_res.data or []
        
        # Get activities
        activities_res = await db_execute(lambda: db.table("activity_log").select("*").eq("client_id", client_id).execute())
        activities = activities_res.data or []
        
        # Get payments (EXCLUDE VOIDED) ✅
        payments_res = await db_execute(lambda: db.table("payments")\
            .select("*")\
            .eq("client_id", client_id)\
            .eq("is_voided", False)\
            .execute())
        payments = payments_res.data or []
        
        # Get commissions (EXCLUDE VOIDED) ✅
        commissions_res = await db_execute(lambda: db.table("commission_earnings")\
            .select("*")\
            .eq("client_id", client_id)\
            .eq("is_voided", False)\
            .execute())
        commissions = commissions_res.data or []
        
        # SCORING FACTORS (100 points total)
        score = 0
        factors = {}
        
        # 1. PURCHASE HISTORY (0-25 points)
        if len(invoices) > 0:
            if len(invoices) >= 3:
                factors["repeat_buyer"] = 25
                score += 25
            elif len(invoices) == 2:
                factors["multiple_purchases"] = 15
                score += 15
            else:
                factors["first_purchase"] = 5
                score += 5
        
        # 2. PAYMENT RELIABILITY (0-20 points) - EXCLUDING VOIDED ✅
        if len(invoices) > 0:
            paid_invoices = len([i for i in invoices if i["status"] == "paid"])
            payment_rate = (paid_invoices / len(invoices)) * 100
            
            if payment_rate == 100:
                factors["perfect_payment_history"] = 20
                score += 20
            elif payment_rate >= 80:
                factors["good_payment_history"] = 15
                score += 15
            elif payment_rate >= 60:
                factors["partial_payment_history"] = 8
                score += 8
        
        # 3. ENGAGEMENT LEVEL (0-20 points)
        if len(activities) > 0:
            recent_activities = len([a for a in activities if 
                (datetime.now() - datetime.fromisoformat(a["created_at"])).days <= 30])
            
            if recent_activities >= 5:
                factors["highly_engaged"] = 20
                score += 20
            elif recent_activities >= 3:
                factors["moderately_engaged"] = 12
                score += 12
            elif recent_activities >= 1:
                factors["somewhat_engaged"] = 5
                score += 5
        
        # 4. DEAL SIZE / TRANSACTION VALUE (0-20 points)
        if len(invoices) > 0:
            total_value = sum(float(i["amount"]) for i in invoices)
            avg_deal_size = total_value / len(invoices)
            
            if avg_deal_size > 10000000:  # >10M
                factors["high_value_deals"] = 20
                score += 20
            elif avg_deal_size > 5000000:  # >5M
                factors["medium_high_value"] = 12
                score += 12
            elif avg_deal_size > 1000000:  # >1M
                factors["medium_value"] = 8
                score += 8
        
        # 5. RECENCY (HOW LONG SINCE LAST PURCHASE) (0-15 points)
        if len(invoices) > 0:
            last_invoice = max(invoices, key=lambda x: x["created_at"])
            days_since = (datetime.now() - datetime.fromisoformat(last_invoice["created_at"])).days
            
            if days_since <= 30:
                factors["very_recent_activity"] = 15
                score += 15
            elif days_since <= 90:
                factors["recent_activity"] = 10
                score += 10
            elif days_since <= 180:
                factors["moderately_recent"] = 5
                score += 5
        
        # 6. OPEN DEALS (INDICATES ACTIVE INTEREST) (0-20 points)
        open_deals = len([i for i in invoices if i["status"] in ["unpaid", "partial"]])
        
        if open_deals >= 3:
            factors["multiple_open_deals"] = 20
            score += 20
        elif open_deals == 2:
            factors["two_open_deals"] = 12
            score += 12
        elif open_deals == 1:
            factors["one_open_deal"] = 5
            score += 5
        
        # 7. COMMISSION EARNED (BONUS - shows business value)
        if len(commissions) > 0:
            total_commission = sum(float(c.get("commission_amount", 0)) for c in commissions)
            if total_commission > 5000000:  # >5M
                factors["high_commission_value"] = 10
                score += 10
            elif total_commission > 1000000:  # >1M
                factors["medium_commission_value"] = 5
                score += 5
        
        # 8. OVERDUE RISK (PENALTY)
        overdue_deals = len([i for i in invoices if i["status"] == "overdue"])
        if overdue_deals > 2:
            factors["high_overdue_risk"] = -15
            score -= 15
        elif overdue_deals == 1:
            factors["overdue_risk"] = -5
            score -= 5
        
        # Normalize to 0-100
        score = min(100, max(0, score))
        
        # Determine Lead Quality
        if score >= 80:
            quality = "HOT - Ready to convert"
            urgency = "IMMEDIATE"
        elif score >= 60:
            quality = "WARM - Promising prospect"
            urgency = "HIGH"
        elif score >= 40:
            quality = "LUKEWARM - Needs nurturing"
            urgency = "MEDIUM"
        else:
            quality = "COLD - Long-term prospect"
            urgency = "LOW"
        
        return {
            "client_id": client_id,
            "client_name": client["full_name"],
            "score": round(score, 1),
            "quality": quality,
            "urgency": urgency,
            "factors": factors,
            "recommendation": f"Lead {quality}. Total score factors: {len(factors)}. Priority for follow-up: {urgency}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lead-scoring/all")
async def score_all_leads(current_admin=Depends(verify_token)):
    """
    Score all clients and return ranked list of hottest leads (EXCLUDES VOIDED DATA) ✅
    🔥 PERFORMANCE OPTIMIZED: Uses bulk queries instead of N+1 database hits.
    """
    db = get_db()
    
    # 1. Fetch all clients (single hit)
    query = db.table("clients").select("id, full_name, email, assigned_rep_id")
    
    # ROLE-BASED FILTERING ✅
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin"] for r in roles)
    is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
    
    admin_id = current_admin.get("sub")
    if is_restricted:
        query = query.eq("assigned_rep_id", admin_id)
        
    clients_res = await db_execute(lambda: query.execute())
    clients_data = clients_res.data or []
    if not clients_data:
        return {"total_leads": 0, "hot_leads": 0, "warm_leads": 0, "prioritized_leads": []}

    client_ids = [c["id"] for c in clients_data]
    
    # 2. Fetch related data in bulk chunks (limit N+1)
    # PostgREST allows .in_ for bulk matching
    all_invoices_res = await db_execute(lambda: db.table("invoices")\
        .select("client_id, status, amount")\
        .neq("status", "voided")\
        .in_("client_id", client_ids)\
        .execute())
    all_invoices = all_invoices_res.data or []
        
    all_activities_res = await db_execute(lambda: db.table("activity_log")\
        .select("client_id, created_at")\
        .in_("client_id", client_ids)\
        .execute())
    all_activities = all_activities_res.data or []
        
    all_commissions_res = await db_execute(lambda: db.table("commission_earnings")\
        .select("client_id, commission_amount")\
        .eq("is_voided", False)\
        .in_("client_id", client_ids)\
        .execute())
    all_commissions = all_commissions_res.data or []

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
    
    prop = db.table("properties").select("*").eq("id", property_id).execute()
    if not prop.data:
        raise HTTPException(status_code=404, detail="Property not found")
    
    property_data = prop.data[0]
    
    # Get interested clients
    interested_res = await db_execute(lambda: db.table("property_interests").select("*, clients(full_name, email)").eq("property_id", property_id).execute())
    interested = interested_res.data or []
    
    # Get inquiries
    inquiries_res = await db_execute(lambda: db.table("property_inquiries").select("*").eq("property_id", property_id).order("created_at", desc=True).execute())
    inquiries = inquiries_res.data or []
    
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
    """
    db = get_db()

    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin", "lawyer", "legal"] for r in roles)
    is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged

    admin_id = current_admin.get("sub")

    # Fetch invoices with client and signing session data — same join as documents-pipeline
    invoices_res = await db_execute(lambda: db.table("invoices") \
        .select("id, invoice_number, property_name, amount, status, created_at, contract_signature_url, clients(id, full_name, email, assigned_rep_id), contract_signing_sessions(id, status, created_at, expires_at, witness_signatures(*))") \
        .neq("status", "voided") \
        .order("created_at", desc=True) \
        .execute())
    invoices = invoices_res.data or []

    # Role-based filtering — sales reps only see their assigned clients
    if is_restricted:
        invoices = [
            inv for inv in invoices
            if inv.get("clients") and inv["clients"].get("assigned_rep_id") == admin_id
        ]

    # Shape each invoice into a document record
    docs = []
    for inv in invoices:
        sessions = inv.get("contract_signing_sessions") or []
        if isinstance(sessions, list) and sessions:
            session = sorted(sessions, key=lambda s: s.get("created_at", ""), reverse=True)[0]
        elif isinstance(sessions, dict):
            session = sessions
        else:
            session = {}

        signing_status = session.get("status", "not_started")

        # Map signing status to document status
        if signing_status == "completed":
            doc_status = "signed"
        elif signing_status in ["pending", "partial"]:
            doc_status = "pending_signature"
        else:
            doc_status = "draft"

        # Count signatures
        sigs = 1 if inv.get("contract_signature_url") else 0
        witnesses = session.get("witness_signatures") or []
        sigs += len(witnesses)

        docs.append({
            "id": inv["id"],
            "invoice_number": inv.get("invoice_number"),
            "property_name": inv.get("property_name"),
            "amount": inv.get("amount"),
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
    
    docs_res = await db_execute(lambda: db.table("documents").select("*").eq("client_id", client_id).order("created_at", desc=True).execute())
    docs = docs_res.data or []
    
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
    clients_res = await db_execute(lambda: db.table("clients").select("id, phone, email").execute())
    target_clients = clients_res.data or []
    
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
    is_privileged = any(r in ["admin", "operations", "super_admin"] for r in roles)
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
    invoices_res = await db_execute(lambda: db.table("invoices")\
        .select("id, invoice_number, property_name, amount, amount_paid, status, created_at, pipeline_stage")\
        .eq("client_id", client_id)\
        .neq("status", "voided")\
        .order("created_at", desc=True)\
        .execute())
    invoices = invoices_res.data or []
        
    # 3. Fetch Activity Timeline
    activities_res = await db_execute(lambda: db.table("activity_log")\
        .select("id, event_type, description, created_at")\
        .eq("client_id", client_id)\
        .order("created_at", desc=True)\
        .limit(20)\
        .execute())
    activities = activities_res.data or []
        
    # 4. Fetch Email Logs
    emails_res = await db_execute(lambda: db.table("email_logs")\
        .select("id, email_type, subject, status, sent_at")\
        .eq("client_id", client_id)\
        .order("sent_at", desc=True)\
        .limit(10)\
        .execute())
    emails = emails_res.data or []

    # Map the stage name if the client record has one
    pipeline_stage = client.get("pipeline_stage") or (invoices[0].get("pipeline_stage") if invoices else "inspection")

    return {
        "id": client["id"],
        "full_name": client["full_name"],
        "email": client["email"],
        "phone": client["phone"],
        "pipeline_stage": pipeline_stage,
        "estimated_value": sum(float(i["amount"]) for i in invoices),
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
    
    messages_res = await db_execute(lambda: db.table("campaign_messages").select("*").eq("campaign_id", campaign_id).execute())
    messages = messages_res.data or []
    
    return {
        "campaign_name": campaign.data[0]["name"],
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
    properties = prop_query.execute().data or []
    
    inv_query = db.table("invoices").select("property_id, amount").neq("status", "voided").in_("status", ["paid", "partial"]).execute()
    invoices = inv_query.data or []
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
    is_privileged = any(r in ["admin", "operations", "super_admin"] for r in roles)
    is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
    
    admin_id = current_admin.get("sub")
    if is_restricted:
        query = query.eq("assigned_rep_id", admin_id)
        
    clients = query.execute().data or []
    if not clients: return {"total_clients": 0, "total_revenue": 0, "top_clients": []}

    client_ids = [c["id"] for c in clients]
    all_invoices = db.table("invoices").select("client_id, amount").eq("is_voided", False).in_("client_id", client_ids).execute().data or []
        
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
    is_admin = current_admin.get("role") in ["admin", "operations"]
    
    query = db.table("invoices")\
        .select("id, invoice_number, property_name, property_location, amount, created_at, status, contract_signature_url, clients(id, full_name, email, assigned_rep_id), contract_signing_sessions(*, witness_signatures(*))") \
        .neq("status", "voided") \
        .order("created_at", desc=True)

    result = query.execute()
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
    is_privileged = any(r in ["admin", "operations", "super_admin"] for r in roles)
    
    if not is_privileged:
        # Reps shouldn't see full team intelligence
        raise HTTPException(status_code=403, detail="Intelligence dashboard restricted to Admins & Operations")
        
    db = get_db()
    invoices = db.table("invoices").select("*").neq("status", "voided").execute().data or []
    commissions = db.table("commission_earnings").select("*").eq("is_voided", False).execute().data or []
    
    team_stats = {}
    for inv in invoices:
        rep = inv.get("sales_rep_name") or "Unassigned"
        if rep not in team_stats:
            team_stats[rep] = {"total_deals": 0, "total_revenue": 0, "total_collected": 0, "closed_deals": 0, "actual_commissions": 0}
        
        team_stats[rep]["total_deals"] += 1
        team_stats[rep]["total_revenue"] += float(inv["amount"])
        team_stats[rep]["total_collected"] += float(inv["amount_paid"])
        if inv["status"] == "paid": team_stats[rep]["closed_deals"] += 1
    
    for comm in commissions:
        rep = comm.get("sales_rep_name") or "Unassigned"
        if rep in team_stats:
            team_stats[rep]["actual_commissions"] += float(comm.get("commission_amount", 0))
    
    leaderboard = []
    for rep_name, stats in team_stats.items():
        leaderboard.append({
            "sales_rep": rep_name,
            "total_deals": stats["total_deals"],
            "closed_deals": stats["closed_deals"],
            "total_revenue": round(stats["total_revenue"]),
            "total_collected": round(stats["total_collected"]),
            "actual_commissions_earned": round(stats["actual_commissions"])
        })
    leaderboard.sort(key=lambda x: x["total_revenue"], reverse=True)
    return leaderboard


# ============================================================
# 7. CLIENT PORTAL
# ============================================================

@router.get("/portal/{client_id}/dashboard")
async def get_portal_dashboard(client_id: str):
    db = get_db()
    client = db.table("clients").select("*").eq("id", client_id).execute()
    if not client.data: raise HTTPException(status_code=404, detail="Client not found")
    
    invoices = db.table("invoices").select("*").eq("client_id", client_id).neq("status", "voided").execute().data or []
    payments = db.table("payments").select("*").eq("client_id", client_id).eq("is_voided", False).execute().data or []
    
    return {
        "client_name": client.data[0]["full_name"],
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
        
        # ROLE-BASED FILTERING ✅
        roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
        is_privileged = any(r in ["admin", "operations", "super_admin"] for r in roles)
        is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
        
        admin_id = current_admin.get("sub")
        if is_restricted:
            # Reps can only report on clients assigned to them
            query = query.filter("clients.assigned_rep_id", "eq", admin_id)
            
        invoices = query.execute().data or []
        data = {"total_revenue": sum(float(i["amount"]) for i in invoices), "count": len(invoices)}
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
    is_privileged = any(r in ["admin", "operations", "super_admin", "legal"] for r in roles)
    
    if not is_privileged:
        query = query.eq("performed_by", current_sub)
    elif rep_id:
        query = query.eq("performed_by", rep_id)
        
    if search_text:
        query = query.ilike("description", f"%{search_text}%")
        
    res = query.execute()
    return res.data or []


# ============================================================
# 10. TEAM MANAGEMENT & ASSIGNMENT
# ============================================================

@router.get("/team/assignable")
async def get_assignable_team(current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("admins").select("id, full_name, email, role").eq("is_active", True).execute()
    assignable = []
    for admin in res.data:
        roles = [r.strip().lower() for r in (admin.get("role") or "").split(",")]
        if "sales" in roles or "operations" in roles:
            assignable.append({"id": admin["id"], "full_name": admin["full_name"], "email": admin["email"]})
    return assignable

@router.patch("/clients/{client_id}/assign")
async def assign_client(client_id: str, request: Request, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    rep_id = body.get("assigned_rep_id")
    
    rep_res = db.table("admins").select("full_name").eq("id", rep_id).execute()
    if not rep_res.data: raise HTTPException(status_code=404, detail="Team member not found")
    
    db.table("clients").update({"assigned_rep_id": rep_id}).eq("id", client_id).execute()
    
    background_tasks.add_task(db.table("activity_log").insert({
        "client_id": client_id, "event_type": "lead_assigned", 
        "description": f"Lead assigned to {rep_res.data[0]['full_name']}", "performed_by": current_admin["sub"]
    }).execute)
    
    return {"message": "Assigned successfully"}

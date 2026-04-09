from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from database import get_db
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
        client = db.table("clients").select("*").eq("id", client_id).execute()
        if not client.data:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client = client.data[0]
        
        # Get invoices (EXCLUDE VOIDED) ✅
        invoices = db.table("invoices")\
            .select("*")\
            .eq("client_id", client_id)\
            .neq("status", "voided")\
            .execute().data or []
        
        # Get activities
        activities = db.table("activity_log").select("*").eq("client_id", client_id).execute().data or []
        
        # Get payments (EXCLUDE VOIDED) ✅
        payments = db.table("payments")\
            .select("*")\
            .eq("client_id", client_id)\
            .eq("is_voided", False)\
            .execute().data or []
        
        # Get commissions (EXCLUDE VOIDED) ✅
        commissions = db.table("commission_earnings")\
            .select("*")\
            .eq("client_id", client_id)\
            .eq("is_voided", False)\
            .execute().data or []
        
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
    clients_data = db.table("clients").select("id, full_name, email").execute().data or []
    if not clients_data:
        return {"total_leads": 0, "hot_leads": 0, "warm_leads": 0, "prioritized_leads": []}

    client_ids = [c["id"] for c in clients_data]
    
    # 2. Fetch related data in bulk chunks (limit N+1)
    # PostgREST allows .in_ for bulk matching
    all_invoices = db.table("invoices")\
        .select("client_id, status, amount")\
        .neq("status", "voided")\
        .in_("client_id", client_ids)\
        .execute().data or []
        
    all_activities = db.table("activity_log")\
        .select("client_id, created_at")\
        .in_("client_id", client_ids)\
        .execute().data or []
        
    all_commissions = db.table("commission_earnings")\
        .select("client_id, commission_amount")\
        .eq("is_voided", False)\
        .in_("client_id", client_ids)\
        .execute().data or []

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
    
    result = db.table("properties").insert(property_data).execute()
    
    return {
        "status": "created",
        "property_id": result.data[0]["id"],
        "property": result.data[0]
    }


@router.post("/properties")
async def create_property(
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
    
    result = db.table("properties").insert(payload).execute()
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
    
    result = query.order("created_at", desc=True).execute()
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
    interested = db.table("property_interests").select("*, clients(full_name, email)").eq("property_id", property_id).execute().data or []
    
    # Get inquiries
    inquiries = db.table("property_inquiries").select("*").eq("property_id", property_id).order("created_at", desc=True).execute().data or []
    
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
    
    result = db.table("property_media").insert(media_item).execute()
    
    return {"status": "media_added", "media": result.data[0]}


# ============================================================
# 3. DOCUMENT MANAGEMENT & E-SIGNATURES
# ============================================================

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
    
    result = db.table("documents").insert(doc).execute()
    
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
    db.table("documents").update({
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
        "sent_to_email": body.get("email"),
        "esignature_link": f"https://esign.yourapp.com/{document_id}"
    }).eq("id", document_id).execute()
    
    # In real system, integrate with DocuSign, Adobe Sign, or HelloSign
    # For now, log the action
    db.table("activity_log").insert({
        "event_type": "document_sent_for_signature",
        "description": f"Document sent for e-signature: {body.get('email')}",
        "client_id": body.get("client_id"),
        "document_id": document_id,
        "performed_by": current_admin["sub"]
    }).execute()
    
    return {"status": "document_sent", "esignature_link": f"https://esign.yourapp.com/{document_id}"}


@router.get("/documents/{client_id}")
async def get_client_documents(
    client_id: str,
    current_admin=Depends(verify_token)
):
    """Get all documents for a client"""
    db = get_db()
    
    docs = db.table("documents").select("*").eq("client_id", client_id).order("created_at", desc=True).execute().data or []
    
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
        "target_segment": body.get("target_segment"),  # "hot_leads", "warm_leads", "past_buyers", "old_leads"
        "message_template": body.get("message_template"),
        "schedule": body.get("schedule"),  # "immediate", "daily", "weekly"
        "schedule_time": body.get("schedule_time"),
        "created_by": current_admin["sub"],
        "status": "draft",
        "created_at": datetime.now().isoformat()
    }
    
    result = db.table("campaigns").insert(campaign).execute()
    
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
    
    campaign = db.table("campaigns").select("*").eq("id", campaign_id).execute()
    if not campaign.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = campaign.data[0]
    
    # Get target contacts based on segment
    if campaign["target_segment"] == "hot_leads":
        # Get high-score leads (simplified)
        target_clients = db.table("clients").select("id, phone, email").execute().data or []
    else:
        target_clients = db.table("clients").select("id, phone, email").execute().data or []
    
    # In production, integrate with Twilio (SMS) and SendGrid/Mailgun (Email)
    sent_count = 0
    for client in target_clients:
        # Log message sent
        db.table("campaign_messages").insert({
            "campaign_id": campaign_id,
            "client_id": client["id"],
            "type": campaign["type"],
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }).execute()
        sent_count += 1
    
    # Update campaign status
    db.table("campaigns").update({
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
        "messages_sent": sent_count
    }).eq("id", campaign_id).execute()
    
    return {
        "status": "campaign_sent",
        "messages_sent": sent_count,
        "campaign_name": campaign["name"]
    }


@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: str,
    current_admin=Depends(verify_token)
):
    """Get campaign performance metrics"""
    db = get_db()
    
    campaign = db.table("campaigns").select("*").eq("id", campaign_id).execute()
    if not campaign.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    messages = db.table("campaign_messages").select("*").eq("campaign_id", campaign_id).execute().data or []
    
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
    """
    Market data, trends, neighborhood insights
    ✅ REAL DATA: Uses invoices to calculate selling rate
    """
    db = get_db()
    
    # 1. Get properties
    prop_query = db.table("properties").select("*")
    if location:
        prop_query = prop_query.ilike("location", f"%{location}%")
    properties = prop_query.execute().data or []
    
    # 2. Get active invoices (Sold units)
    # We consider property 'sold' if there is an invoice that is NOT voided and at least partial/paid
    inv_query = db.table("invoices").select("property_id")\
        .neq("status", "voided")\
        .in_("status", ["paid", "partial"])\
        .execute()
    
    sold_property_ids = {i["property_id"] for i in inv_query.data if i.get("property_id")}
    
    # 3. Calculate market metrics
    prices = [float(p["starting_price"]) for p in properties if p.get("starting_price")]
    avg_price = statistics.mean(prices) if prices else 0
    median_price = statistics.median(prices) if prices else 0
    
    total_listings = len(properties)
    sold_count = 0
    available_count = 0
    
    if total_listings > 0:
        # Match properties with sold status
        for p in properties:
            if p["id"] in sold_property_ids:
                sold_count += 1
            else:
                available_count += 1
    
    # Simulated Days on Market - Improvement for future: calculate from created_at vs invoice date
    avg_days_on_market = 45 
    
    return {
        "market_summary": {
            "location": location or "All Territories",
            "total_listings": total_listings,
            "available": available_count,
            "sold": sold_count,
            "average_price": round(avg_price),
            "median_price": round(median_price),
            "average_days_on_market": avg_days_on_market,
            "selling_rate_percent": round((sold_count / total_listings * 100)) if total_listings > 0 else 0
        },
        "market_health": "Strong" if (sold_count / total_listings if total_listings > 0 else 0) > 0.3 else "Steady",
        "trends": {
            "price_trend": "↑ Increasing" if avg_price > 5000000 else "→ Stable",
            "inventory": "Healthy" if available_count > 5 else "Limited"
        }
    }


@router.get("/analytics/client-lifetime-value")
async def get_client_ltv_analysis(current_admin=Depends(verify_token)):
    """
    Analyze client lifetime value segments
    ✅ PERFORMANCE OPTIMIZED: Fetches all invoice data in bulk.
    """
    db = get_db()
    
    clients = db.table("clients").select("id, full_name").execute().data or []
    if not clients:
        return {"total_clients": 0, "total_revenue": 0, "top_clients": []}

    client_ids = [c["id"] for c in clients]
    
    # Bulk fetch invoices EXCLUDING VOIDED ✅
    all_invoices = db.table("invoices")\
        .select("client_id, amount")\
        .eq("is_voided", False)\
        .in_("client_id", client_ids)\
        .execute().data or []
        
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
    
    high_value = len([c for c in ltv_analysis if c["segment"] == "High Value"])
    medium_value = len([c for c in ltv_analysis if c["segment"] == "Medium Value"])
    standard = len([c for c in ltv_analysis if c["segment"] == "Standard"])
    
    return {
        "total_clients": len(ltv_analysis),
        "high_value_clients": high_value,
        "medium_value_clients": medium_value,
        "standard_clients": standard,
        "total_revenue": sum(float(c["lifetime_value"]) for c in ltv_analysis),
        "top_clients": ltv_analysis[:10]
    }


@router.get("/documents")
async def list_documents(current_admin=Depends(verify_token)):
    """
    Consolidated view of all legal and transaction documents.
    ✅ PERFORMANCE OPTIMIZED
    """
    db = get_db()
    
    # Fetch contract documents with joins
    res = db.table("contract_documents")\
        .select("*, invoices(invoice_number, clients(full_name))")\
        .order("created_at", desc=True)\
        .execute()
    
    return res.data


# ============================================================
# 6. TEAM PERFORMANCE & COMMISSIONS
# ============================================================

@router.get("/analytics/team-performance")
async def get_team_comprehensive_performance(current_admin=Depends(verify_token)):
    """
    Comprehensive team leaderboard with all metrics
    ✅ EXCLUDES VOIDED INVOICES and VOIDED COMMISSIONS
    """
    db = get_db()
    
    # Get invoices EXCLUDING VOIDED ✅
    invoices = db.table("invoices").select("*").neq("status", "voided").execute().data or []
    
    # Get actual commission earnings EXCLUDING VOIDED ✅
    commissions = db.table("commission_earnings")\
        .select("*")\
        .eq("is_voided", False)\
        .execute().data or []
    
    # Group by sales rep
    team_stats = {}
    for inv in invoices:
        rep = inv.get("sales_rep_name") or "Unassigned"
        if rep not in team_stats:
            team_stats[rep] = {
                "total_deals": 0,
                "total_revenue": 0,
                "total_collected": 0,
                "closed_deals": 0,
                "pending_deals": 0,
                "overdue_deals": 0,
                "actual_commissions": 0
            }
        
        team_stats[rep]["total_deals"] += 1
        team_stats[rep]["total_revenue"] += float(inv["amount"])
        team_stats[rep]["total_collected"] += float(inv["amount_paid"])
        
        if inv["status"] == "paid":
            team_stats[rep]["closed_deals"] += 1
        elif inv["status"] in ["unpaid", "partial"]:
            team_stats[rep]["pending_deals"] += 1
        elif inv["status"] == "overdue":
            team_stats[rep]["overdue_deals"] += 1
    
    # Add actual commission earnings
    for comm in commissions:
        rep = comm.get("sales_rep_name") or "Unassigned"
        if rep not in team_stats:
            team_stats[rep] = {
                "total_deals": 0,
                "total_revenue": 0,
                "total_collected": 0,
                "closed_deals": 0,
                "pending_deals": 0,
                "overdue_deals": 0,
                "actual_commissions": 0
            }
        team_stats[rep]["actual_commissions"] += float(comm.get("commission_amount", 0))
    
    # Calculate KPIs
    leaderboard = []
    for rep_name, stats in team_stats.items():
        conversion_rate = (stats["closed_deals"] / stats["total_deals"] * 100) if stats["total_deals"] > 0 else 0
        avg_deal_size = stats["total_revenue"] / stats["total_deals"] if stats["total_deals"] > 0 else 0
        collection_rate = (stats["total_collected"] / stats["total_revenue"] * 100) if stats["total_revenue"] > 0 else 0
        
        leaderboard.append({
            "sales_rep": rep_name,
            "total_deals": stats["total_deals"],
            "closed_deals": stats["closed_deals"],
            "pending_deals": stats["pending_deals"],
            "overdue_deals": stats["overdue_deals"],
            "total_revenue": round(stats["total_revenue"]),
            "total_collected": round(stats["total_collected"]),
            "avg_deal_size": round(avg_deal_size),
            "conversion_rate": round(conversion_rate, 1),
            "collection_rate": round(collection_rate, 1),
            "actual_commissions_earned": round(stats["actual_commissions"])  # Real data ✅
        })
    
    leaderboard.sort(key=lambda x: x["total_revenue"], reverse=True)
    
    return {
        "total_team_members": len(leaderboard),
        "total_team_revenue": sum(s["total_revenue"] for s in leaderboard),
        "total_team_commissions": sum(s["actual_commissions_earned"] for s in leaderboard),
        "top_performer": leaderboard[0] if leaderboard else None,
        "team_leaderboard": leaderboard
    }


# ============================================================
# 7. CLIENT PORTAL
# ============================================================

@router.get("/portal/{client_id}/dashboard")
async def get_client_portal_dashboard(
    client_id: str,
    request: Request
):
    """
    Client-facing portal showing their transactions
    ✅ EXCLUDES VOIDED INVOICES and VOIDED PAYMENTS
    """
    db = get_db()
    
    client = db.table("clients").select("*").eq("id", client_id).execute()
    if not client.data:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get invoices EXCLUDING VOIDED ✅
    invoices = db.table("invoices")\
        .select("*")\
        .eq("client_id", client_id)\
        .neq("status", "voided")\
        .execute().data or []
    
    # Get payments EXCLUDING VOIDED ✅
    payments = db.table("payments")\
        .select("*")\
        .eq("client_id", client_id)\
        .eq("is_voided", False)\
        .execute().data or []
    
    # Get documents
    documents = db.table("documents").select("*").eq("client_id", client_id).execute().data or []
    
    total_invoices = sum(float(i["amount"]) for i in invoices)
    total_payments = sum(float(p["amount"]) for p in payments)
    
    return {
        "client_name": client.data[0]["full_name"],
        "summary": {
            "total_deals": len(invoices),
            "total_amount": round(total_invoices),
            "total_paid": round(total_payments),
            "balance": round(total_invoices - total_payments)
        },
        "recent_invoices": invoices[-5:],
        "recent_payments": payments[-5:],
        "pending_documents": [d for d in documents if d["status"] in ["draft", "sent"]],
        "signed_documents": [d for d in documents if d["status"] == "signed"]
    }


# ============================================================
# 8. CUSTOM REPORTING & EXPORTS
# ============================================================

@router.post("/reports/generate")
async def generate_custom_report(
    request: Request,
    current_admin=Depends(verify_token)
):
    """
    Generate professional reports (PDF/Excel export ready)
    ✅ EXCLUDES VOIDED INVOICES
    """
    db = get_db()
    body = await request.json()
    
    report_type = body.get("report_type")  # "sales", "team", "property", "client", "market"
    date_range = body.get("date_range")  # "this_month", "this_quarter", "this_year"
    
    if report_type == "sales":
        # Get invoices EXCLUDING VOIDED ✅
        invoices = db.table("invoices")\
            .select("*")\
            .neq("status", "voided")\
            .execute().data or []
        
        report_data = {
            "total_sales": len(invoices),
            "total_revenue": round(sum(float(i["amount"]) for i in invoices)),
            "total_collected": round(sum(float(i["amount_paid"]) for i in invoices)),
            "average_deal_size": round(sum(float(i["amount"]) for i in invoices) / len(invoices)) if invoices else 0,
            "by_status": {
                "paid": len([i for i in invoices if i["status"] == "paid"]),
                "unpaid": len([i for i in invoices if i["status"] == "unpaid"]),
                "partial": len([i for i in invoices if i["status"] == "partial"]),
                "overdue": len([i for i in invoices if i["status"] == "overdue"])
            }
        }
    elif report_type == "team":
        # Get invoices EXCLUDING VOIDED ✅
        invoices = db.table("invoices")\
            .select("*")\
            .neq("status", "voided")\
            .execute().data or []
        # Group by rep (simplified)
        report_data = {"team_performance": "See /analytics/team-performance"}
    
    report = {
        "report_id": f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "report_type": report_type,
        "date_range": date_range,
        "generated_by": current_admin["sub"],
        "generated_at": datetime.now().isoformat(),
        "data": report_data,
        "export_url": f"/reports/export/pdf/RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    return report


@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: str,
    format: str = "pdf",
    current_admin=Depends(verify_token)
):
    """Export report as PDF or Excel"""
    # In production, use reportlab (PDF) or openpyxl (Excel)
    # For now, return download URL
    return {
        "status": "ready_for_download",
        "download_url": f"/downloads/{report_id}.{format}",
        "format": format
    }

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
    """
    db = get_db()
    
    try:
        client_res = await db_execute(lambda: db.table("clients").select("*").eq("id", client_id).execute())
        if not client_res.data:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client = client_res.data[0]
        
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
        
        # 2. PAYMENT RELIABILITY (0-20 points)
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
            now = datetime.now()
            recent_acts = []
            for a in activities:
                try:
                    if (now - datetime.fromisoformat(a["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)).days <= 30:
                        recent_acts.append(a)
                except: continue
            
            recent_count = len(recent_acts)
            if recent_count >= 5:
                factors["highly_engaged"] = 20
                score += 20
            elif recent_count >= 3:
                factors["moderately_engaged"] = 12
                score += 12
            elif recent_count >= 1:
                factors["somewhat_engaged"] = 5
                score += 5
        
        # 4. DEAL SIZE / TRANSACTION VALUE (0-20 points)
        if len(invoices) > 0:
            total_value = sum(float(i["amount"]) for i in invoices)
            avg_deal_size = total_value / len(invoices)
            
            if avg_deal_size > 10000000:
                factors["high_value_deals"] = 20
                score += 20
            elif avg_deal_size > 5000000:
                factors["medium_high_value"] = 12
                score += 12
            elif avg_deal_size > 1000000:
                factors["medium_value"] = 8
                score += 8
        
        # 5. RECENCY (0-15 points)
        if len(invoices) > 0:
            last_invoice = max(invoices, key=lambda x: x["created_at"])
            days_since = (datetime.now() - datetime.fromisoformat(last_invoice["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)).days
            
            if days_since <= 30:
                factors["very_recent_activity"] = 15
                score += 15
            elif days_since <= 90:
                factors["recent_activity"] = 10
                score += 10
            elif days_since <= 180:
                factors["moderately_recent"] = 5
                score += 5
        
        # 6. OPEN DEALS (0-20 points)
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
            
        # 7. COMMISSION BONUS
        if len(commissions) > 0:
            total_comm = sum(float(c.get("commission_amount", 0)) for c in commissions)
            if total_comm > 5000000:
                factors["high_commission_value"] = 10
                score += 10
            elif total_comm > 1000000:
                factors["medium_commission_value"] = 5
                score += 5
                
        # 8. OVERDUE RISK
        overdue_deals = len([i for i in invoices if i["status"] == "overdue"])
        if overdue_deals > 2:
            factors["high_overdue_risk"] = -15
            score -= 15
        elif overdue_deals == 1:
            factors["overdue_risk"] = -5
            score -= 5
            
        score = min(100, max(0, score))
        
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
    """Score all clients and return ranked list of hottest leads"""
    db = get_db()
    
    # 1. Fetch all clients
    query = db.table("clients").select("id, full_name, email, assigned_rep_id")
    
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
    
    # 2. Fetch related data in bulk
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

    # 3. Create indices
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

    # 4. Calculate scores
    scored_leads = []
    now = datetime.now()
    
    for client in clients_data:
        cid = client["id"]
        invoices = inv_map.get(cid, [])
        activities = act_map.get(cid, [])
        commissions = comm_map.get(cid, [])
        
        score = 0
        score += min(25, len(invoices) * 8)
        
        recent_acts = []
        for a in activities:
            try:
                if (now - datetime.fromisoformat(a["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)).days <= 30:
                    recent_acts.append(a)
            except: continue
        
        score += len(recent_acts) * 2
        
        if invoices:
            paid = len([i for i in invoices if i["status"] == "paid"])
            score += (paid / len(invoices)) * 20
        
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
    
    scored_leads.sort(key=lambda x: x["score"], reverse=True)
    return {
        "total_leads": len(scored_leads),
        "hot_leads": len([l for l in scored_leads if l["score"] >= 80]),
        "warm_leads": len([l for l in scored_leads if 60 <= l["score"] < 80]),
        "prioritized_leads": scored_leads[:20]
    }

# ============================================================
# 2. PROPERTY MANAGEMENT
# ============================================================

@router.post("/properties")
async def create_property(request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    property_data = {
        "address": body.get("address"),
        "city": body.get("city"),
        "state": body.get("state"),
        "property_type": body.get("property_type"),
        "bedrooms": body.get("bedrooms"),
        "bathrooms": body.get("bathrooms"),
        "sq_feet": body.get("sq_feet"),
        "price": body.get("price"),
        "description": body.get("description"),
        "owner_agent_id": current_admin["sub"],
        "status": "available",
        "photos": body.get("photos", []),
        "virtual_tour_url": body.get("virtual_tour_url"),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    result = await db_execute(lambda: db.table("properties").insert(property_data).execute())
    return {"status": "created", "property": result.data[0]}

@router.post("/properties/v2")
async def create_property_v2(data: PropertyCreate, current_admin=Depends(verify_token)):
    db = get_db()
    payload = data.dict()
    payload["created_at"] = datetime.now().isoformat()
    payload["updated_at"] = datetime.now().isoformat()
    result = await db_execute(lambda: db.table("properties").insert(payload).execute())
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create property")
    return result.data[0]

@router.get("/properties")
async def list_properties(property_type: Optional[str] = None, status: Optional[str] = None, include_archived: bool = False, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("properties").select("*")
    if not include_archived: query = query.eq("is_active", True)
    if property_type: query = query.eq("property_type", property_type)
    if status: query = query.eq("status", status)
    result = await db_execute(lambda: query.order("created_at", desc=True).execute())
    return result.data or []

@router.get("/properties/{property_id}")
async def get_property_details(property_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    prop_res = await db_execute(lambda: db.table("properties").select("*").eq("id", property_id).execute())
    if not prop_res.data:
        raise HTTPException(status_code=404, detail="Property not found")
    interested_res = await db_execute(lambda: db.table("property_interests").select("*, clients(full_name, email)").eq("property_id", property_id).execute())
    inquiries_res = await db_execute(lambda: db.table("property_inquiries").select("*").eq("property_id", property_id).order("created_at", desc=True).execute())
    return {
        "property": prop_res.data[0],
        "interested_clients": interested_res.data or [],
        "inquiries": inquiries_res.data or [],
        "analytics": {
            "total_views": len(inquiries_res.data or []),
            "interested_clients_count": len(interested_res.data or [])
        }
    }

@router.post("/properties/{property_id}/add-media")
async def add_property_media(property_id: str, request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    media_item = {
        "property_id": property_id,
        "type": body.get("type"),
        "url": body.get("url"),
        "description": body.get("description"),
        "order": body.get("order", 0),
        "created_at": datetime.now().isoformat()
    }
    result = await db_execute(lambda: db.table("property_media").insert(media_item).execute())
    return {"status": "media_added", "media": result.data[0]}

# ============================================================
# 3. DOCUMENT MANAGEMENT
# ============================================================

@router.get("/documents")
async def list_all_documents(current_admin=Depends(verify_token)):
    db = get_db()
    roles = [r.strip().lower() for r in (current_admin.get("role") or "").split(",")]
    is_privileged = any(r in ["admin", "operations", "super_admin"] for r in roles)
    is_restricted = any(r in ["sales", "staff"] for r in roles) and not is_privileged
    admin_id = current_admin.get("sub")
    if is_restricted:
        clients_res = await db_execute(lambda: db.table("clients").select("id").eq("assigned_rep_id", admin_id).execute())
        client_ids = [c["id"] for c in clients_res.data or []]
        if not client_ids:
            return {"total_documents": 0, "documents": []}
        docs_res = await db_execute(lambda: db.table("documents").select("*, clients(id, full_name, email)").in_("client_id", client_ids).order("created_at", desc=True).execute())
    else:
        docs_res = await db_execute(lambda: db.table("documents").select("*, clients(id, full_name, email)").order("created_at", desc=True).execute())
    docs = docs_res.data or []
    return {
        "total_documents": len(docs),
        "draft": len([d for d in docs if d["status"] == "draft"]),
        "sent": len([d for d in docs if d["status"] == "sent"]),
        "signed": len([d for d in docs if d["status"] == "signed"]),
        "documents": docs
    }

@router.post("/documents")
async def upload_document(request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    doc = {
        "document_type": body.get("document_type"),
        "client_id": body.get("client_id"),
        "title": body.get("title"),
        "file_url": body.get("file_url"),
        "status": "draft",
        "created_by": current_admin["sub"],
        "created_at": datetime.now().isoformat()
    }
    result = await db_execute(lambda: db.table("documents").insert(doc).execute())
    return {"status": "uploaded", "document": result.data[0]}

@router.post("/documents/{document_id}/send-for-signature")
async def send_document_for_esignature(document_id: str, request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    await db_execute(lambda: db.table("documents").update({
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
        "sent_to_email": body.get("email"),
        "esignature_link": f"https://esign.yourapp.com/{document_id}"
    }).eq("id", document_id).execute())
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "document_sent",
        "description": f"Document sent for signature: {body.get('email')}",
        "client_id": body.get("client_id"),
        "performed_by": current_admin["sub"]
    }).execute())
    return {"status": "sent"}

@router.get("/documents/{client_id}")
async def get_client_documents(client_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("documents").select("*").eq("client_id", client_id).order("created_at", desc=True).execute())
    docs = res.data or []
    return {"total_documents": len(docs), "documents": docs}

# ============================================================
# 3.5 LEAD DETAIL & PIPELINE DATA
# ============================================================

@router.get("/clients/{client_id}")
async def get_lead_details(client_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("clients").select("*, admins:assigned_rep_id(full_name)").eq("id", client_id).execute())
    if not res.data: raise HTTPException(status_code=404, detail="Lead not found")
    client = res.data[0]
    
    invoices_res = await db_execute(lambda: db.table("invoices").select("*").eq("client_id", client_id).neq("status", "voided").order("created_at", desc=True).execute())
    activities_res = await db_execute(lambda: db.table("activity_log").select("*").eq("client_id", client_id).order("created_at", desc=True).limit(20).execute())
    emails_res = await db_execute(lambda: db.table("email_logs").select("*").eq("client_id", client_id).order("sent_at", desc=True).limit(10).execute())
    
    invoices = invoices_res.data or []
    return {
        "id": client["id"],
        "full_name": client["full_name"],
        "email": client["email"],
        "phone": client["phone"],
        "assigned_rep_name": client["admins"]["full_name"] if client.get("admins") else "Unassigned",
        "activities": activities_res.data or [],
        "invoices": invoices,
        "emails": emails_res.data or [],
        "summary": {
            "total_deals": len(invoices),
            "total_paid": sum(float(i["amount_paid"]) for i in invoices)
        }
    }

# ============================================================
# 4. SMS & EMAIL AUTOMATION CAMPAIGNS
# ============================================================

@router.post("/campaigns/sms")
async def create_sms_campaign(request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    campaign = {
        "type": "sms",
        "name": body.get("name"),
        "target_segment": body.get("target_segment"),
        "message_template": body.get("message_template"),
        "created_by": current_admin["sub"],
        "status": "draft",
        "created_at": datetime.now().isoformat()
    }
    result = await db_execute(lambda: db.table("campaigns").insert(campaign).execute())
    return {"status": "created", "campaign_id": result.data[0]["id"]}

@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str, request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    campaign_res = await db_execute(lambda: db.table("campaigns").select("*").eq("id", campaign_id).execute())
    if not campaign_res.data: raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = campaign_res.data[0]
    
    clients_res = await db_execute(lambda: db.table("clients").select("id").execute())
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
    
    return {"status": "sent", "messages_sent": sent_count}

@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    campaign_res = await db_execute(lambda: db.table("campaigns").select("*").eq("id", campaign_id).execute())
    if not campaign_res.data: raise HTTPException(status_code=404, detail="Campaign not found")
    messages_res = await db_execute(lambda: db.table("campaign_messages").select("*").eq("campaign_id", campaign_id).execute())
    messages = messages_res.data or []
    return {
        "campaign_name": campaign_res.data[0]["name"],
        "total_sent": len(messages),
        "open_rate": f"{(len([m for m in messages if m.get('opened')])/len(messages)*100) if messages else 0}%"
    }

# ============================================================
# 5. ADVANCED ANALYTICS & MARKET INTELLIGENCE
# ============================================================

@router.get("/analytics/market-intelligence")
async def get_market_intelligence(location: Optional[str] = None):
    db = get_db()
    prop_query = db.table("properties").select("*")
    if location: prop_query = prop_query.ilike("location", f"%{location}%")
    properties_res = await db_execute(lambda: prop_query.execute())
    properties = properties_res.data or []
    
    invoices_res = await db_execute(lambda: db.table("invoices").select("property_id, amount").neq("status", "voided").in_("status", ["paid", "partial"]).execute())
    invoices = invoices_res.data or []
    
    prices = [float(i["amount"]) for i in invoices]
    avg_price = statistics.mean(prices) if prices else 0
    
    return {
        "market_summary": {
            "location": location or "All",
            "total_listings": len(properties),
            "average_price": round(avg_price)
        }
    }

@router.get("/analytics/client-lifetime-value")
async def get_client_ltv_analysis(current_admin=Depends(verify_token)):
    db = get_db()
    clients_res = await db_execute(lambda: db.table("clients").select("id, full_name").execute())
    clients = clients_res.data or []
    if not clients: return {"total_clients": 0, "top_clients": []}
    
    client_ids = [c["id"] for c in clients]
    inv_res = await db_execute(lambda: db.table("invoices").select("client_id, amount").eq("is_voided", False).in_("client_id", client_ids).execute())
    invoices = inv_res.data or []
    
    inv_map = {}
    for i in invoices:
        cid = i["client_id"]
        inv_map[cid] = inv_map.get(cid, 0) + float(i["amount"])
    
    ltv_list = []
    for c in clients:
        ltv_list.append({"client_name": c["full_name"], "ltv": inv_map.get(c["id"], 0)})
    
    ltv_list.sort(key=lambda x: x["ltv"], reverse=True)
    return {"top_clients": ltv_list[:10]}

@router.get("/documents-pipeline")
async def list_documents_pipeline(rep_id: Optional[str] = Query(None), search_text: Optional[str] = Query(None), current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("invoices").select("*, clients(id, full_name, assigned_rep_id)").neq("status", "voided")
    res = await db_execute(lambda: query.order("created_at", desc=True).execute())
    contracts = res.data or []
    return [{"invoice_number": c["invoice_number"], "client": c["clients"]["full_name"]} for c in contracts if c.get("clients")]

# ============================================================
# 6. TEAM PERFORMANCE
# ============================================================

@router.get("/analytics/team-performance")
async def get_team_performance(current_admin=Depends(verify_token)):
    db = get_db()
    invoices_res = await db_execute(lambda: db.table("invoices").select("*").neq("status", "voided").execute())
    invoices = invoices_res.data or []
    stats = {}
    for i in invoices:
        rep = i.get("sales_rep_name") or "Unassigned"
        if rep not in stats: stats[rep] = {"revenue": 0, "deals": 0}
        stats[rep]["revenue"] += float(i["amount"])
        stats[rep]["deals"] += 1
    return [{"rep": k, "stats": v} for k, v in stats.items()]

# ============================================================
# 7. CLIENT PORTAL
# ============================================================

@router.get("/portal/{client_id}/dashboard")
async def get_portal_dashboard(client_id: str):
    db = get_db()
    client_res = await db_execute(lambda: db.table("clients").select("full_name").eq("id", client_id).execute())
    if not client_res.data: raise HTTPException(status_code=404, detail="Client not found")
    invoices_res = await db_execute(lambda: db.table("invoices").select("*").eq("client_id", client_id).neq("status", "voided").execute())
    return {"client_name": client_res.data[0]["full_name"], "deals_count": len(invoices_res.data or [])}

# ============================================================
# 8. CUSTOM REPORTING
# ============================================================

@router.post("/reports/generate")
async def generate_report(request: Request, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    invoices_res = await db_execute(lambda: db.table("invoices").select("*").neq("status", "voided").execute())
    return {"generated_at": datetime.now().isoformat(), "total_revenue": sum(float(i["amount"]) for i in invoices_res.data or [])}

# ============================================================
# 9. ACTIVITY LOGS
# ============================================================

@router.get("/activity-logs")
async def get_activity_logs(rep_id: Optional[str] = Query(None), current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("activity_log").select("*, clients(full_name)").order("created_at", desc=True).limit(100)
    if rep_id: query = query.eq("performed_by", rep_id)
    res = await db_execute(lambda: query.execute())
    return res.data or []

# ============================================================
# 10. TEAM MANAGEMENT
# ============================================================

@router.get("/team/assignable")
async def get_assignable_team(current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(lambda: db.table("admins").select("id, full_name, role").eq("is_active", True).execute())
    return res.data or []

@router.patch("/clients/{client_id}/assign")
async def assign_client(client_id: str, request: Request, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    db = get_db()
    body = await request.json()
    rep_id = body.get("assigned_rep_id")
    await db_execute(lambda: db.table("clients").update({"assigned_rep_id": rep_id}).eq("id", client_id).execute())
    return {"message": "Assigned"}

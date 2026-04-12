from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File
from database import get_db, db_execute
from routers.auth import verify_token, require_roles
from datetime import datetime, timedelta
import json
import csv
import io
from typing import List

router = APIRouter()

# ============================================================
# CRM CONTACT & CLIENT MANAGEMENT
# ============================================================

@router.get("/contacts")
async def get_all_contacts(current_admin=Depends(verify_token)):
    """Get all clients with their invoice & payment summary (BULK OPTIMIZED)"""
    db = get_db()
    
    contacts = (await db_execute(lambda: db.table("clients").select("""
        id, full_name, email, phone, city, state, occupation, created_at, updated_at
    """).order("created_at", desc=True).execute())).data or []
    
    if not contacts:
        return []

    client_ids = [c["id"] for c in contacts]
    
    # BULK FETCH: Get all invoices for these clients in ONE hit ✅
    all_invoices = (await db_execute(lambda: db.table("invoices")\
        .select("id, client_id, amount, amount_paid, status")\
        .in_("client_id", client_ids)\
        .execute())).data or []
        
    # Index invoices by client_id in memory
    inv_map = {}
    for inv in all_invoices:
        cid = inv["client_id"]
        if cid not in inv_map: inv_map[cid] = []
        inv_map[cid].append(inv)
    
    # Enrich in-memory (O(N))
    for contact in contacts:
        invoices = inv_map.get(contact["id"], [])
        
        total_value = sum(float(i["amount"]) for i in invoices)
        total_paid = sum(float(i["amount_paid"]) for i in invoices)
        unpaid_count = len([i for i in invoices if i["status"] in ["unpaid", "partial", "overdue"]])
        
        contact["total_value"] = total_value
        contact["amount_paid"] = total_paid
        contact["balance"] = total_value - total_paid
        contact["unpaid_deals"] = unpaid_count
        contact["total_deals"] = len(invoices)
    
    return contacts


@router.get("/contacts/{client_id}")
async def get_contact_details(client_id: str, current_admin=Depends(verify_token)):
    """Get complete client profile with all interactions"""
    db = get_db()
    
    # Get client
    client_result = await db_execute(lambda: db.table("clients").select("*").eq("id", client_id).execute())
    if not client_result.data:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client = client_result.data[0]
    
    invoices = (await db_execute(lambda: db.table("invoices").select("""
        id, 
        invoice_number,
        amount, 
        amount_paid,
        status, 
        invoice_date, 
        due_date,
        payment_terms,
        property_name,
        sales_rep_name,
        created_at
    """).eq("client_id", client_id).order("invoice_date", desc=True).execute())).data or []
    
    # Get all payments
    payments = (await db_execute(lambda: db.table("payments").select("""
        id,
        amount,
        payment_method,
        reference,
        payment_date,
        notes,
        created_at
    """).eq("client_id", client_id).order("payment_date", desc=True).execute())).data or []
    
    # Get all activities
    activities = (await db_execute(lambda: db.table("activity_log").select("""
        id,
        event_type,
        description,
        performed_by,
        created_at,
        metadata
    """).eq("client_id", client_id).order("created_at", desc=True).limit(50).execute())).data or []
    
    # Get email logs
    emails = (await db_execute(lambda: db.table("email_logs").select("""
        id,
        email_type,
        recipient_email,
        subject,
        status,
        sent_at
    """).eq("client_id", client_id).order("sent_at", desc=True).limit(20).execute())).data or []
    
    # Calculate totals
    total_value = sum(float(i["amount"]) for i in invoices)
    total_paid = sum(float(i["amount_paid"]) for i in invoices)
    
    return {
        "client": client,
        "invoices": invoices,
        "payments": payments,
        "activities": activities,
        "emails": emails,
        "summary": {
            "total_value": total_value,
            "total_paid": total_paid,
            "balance": total_value - total_paid,
            "total_deals": len(invoices),
            "paid_deals": len([i for i in invoices if i["status"] == "paid"]),
            "total_interactions": len(activities) + len(emails)
        }
    }


# ============================================================
# SALES PIPELINE & KANBAN
# ============================================================

@router.get("/pipeline")
async def get_sales_pipeline(current_admin=Depends(verify_token)):
    """
    Get all Leads (Clients) grouped by Sales Stage.
    🔒 RBAC: Sales reps only see their assigned leads. Admins see all.
    """
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin.get("sub")
    
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])

    # 1. Base Query
    query = db.table("clients").select("""
        id,
        full_name,
        email,
        phone,
        pipeline_stage,
        estimated_value,
        assigned_rep_id,
        created_at
    """)
    # 2. Apply RBAC Filter
    if not is_privileged:
        query = query.eq("assigned_rep_id", admin_id)

    result = await db_execute(lambda: query.order("created_at", desc=True).execute())
    all_leads = result.data or []

    # 3. Synchronize with real financial data
    client_ids = [c["id"] for c in all_leads]
    if client_ids:
        inv_res = await db_execute(lambda: db.table("invoices").select("client_id, amount, amount_paid").in_("client_id", client_ids).neq("status", "voided").execute())
        invoices_data = inv_res.data or []
    else:
        invoices_data = []
    
    # Map invoice totals to client_id
    fin_map = {}
    for inv in invoices_data:
        cid = inv["client_id"]
        if cid not in fin_map: fin_map[cid] = {"total_amount": 0, "total_paid": 0}
        fin_map[cid]["total_amount"] += float(inv["amount"] or 0)
        fin_map[cid]["total_paid"] += float(inv["amount_paid"] or 0)

    # 4. Group by stage in-memory
    stages = ["inspection", "offer", "contract", "closed"]
    pipeline = {stage: {"deals": [], "count": 0, "total_value": 0} for stage in stages}

    for lead in all_leads:
        stage = lead.get("pipeline_stage")
        if stage in pipeline:
            cid = lead["id"]
            # Use real invoice amount if it exists, fallback to estimated_value
            actual_fin = fin_map.get(cid)
            if actual_fin:
                lead["actual_amount"] = actual_fin["total_amount"]
                lead["actual_paid"] = actual_fin["total_paid"]
                # Use actual for the primary display field
                lead["amount"] = actual_fin["total_amount"]
            else:
                lead["actual_amount"] = 0
                lead["actual_paid"] = 0
                lead["amount"] = lead.get("estimated_value", 0)

            lead["client_name"] = lead.get("full_name")
            
            pipeline[stage]["deals"].append(lead)
            pipeline[stage]["count"] += 1
            pipeline[stage]["total_value"] += float(lead["amount"] or 0)

    return pipeline

@router.post("/import-leads")
async def import_leads_csv(file: UploadFile = File(...), current_admin=Depends(verify_token)):
    """
    Smart CSV Importer for leads with fuzzy header matching.
    """
    db = get_db()
    admin_id = current_admin.get("sub")
    
    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    
    # Header Mapping (Fuzzy Guessing)
    mapping = {
        "full_name": ["name", "full name", "client name", "prospect", "customer name", "contact"],
        "email": ["email", "email address", "mail"],
        "phone": ["phone", "phone number", "mobile", "contact number"],
        "estimated_value": ["value", "budget", "amount", "deal value", "price", "estimated value"],
        "notes": ["notes", "description", "comments", "remark"]
    }

    imported_count = 0
    rows = list(reader)
    
    for row in rows:
        row_lower = {k.lower().strip(): v for k, v in row.items()}
        
        lead_data = {
            "assigned_rep_id": admin_id,
            "pipeline_stage": "inspection",
            "created_at": datetime.now().isoformat()
        }

        for db_field, common_names in mapping.items():
            for possible_name in common_names:
                if possible_name in row_lower:
                    lead_data[db_field] = row_lower[possible_name]
                    break
        
        if lead_data.get("full_name"):
            await db_execute(lambda: db.table("clients").insert(lead_data).execute())
            imported_count += 1

    # Log the bulk action
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "bulk_import",
        "description": f"Imported {imported_count} leads via CSV",
        "performed_by": admin_id,
        "created_at": datetime.now().isoformat()
    }).execute())

    return {"status": "success", "imported": imported_count}

@router.post("/clients")
async def create_lead(data: dict, current_admin=Depends(verify_token)):
    """Create a single lead manually and log the activity."""
    db = get_db()
    admin_id = current_admin["sub"]
    
    data["assigned_rep_id"] = admin_id
    data["created_at"] = datetime.now().isoformat()
    
    res = await db_execute(lambda: db.table("clients").insert(data).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create lead")
    lead = res.data[0]
    
    # Log activity
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "lead_created",
        "description": f"Manual lead creation: {lead.get('full_name')}",
        "client_id": lead["id"],
        "performed_by": admin_id,
        "created_at": datetime.now().isoformat()
    }).execute())
    
    return lead

@router.put("/pipeline/{client_id}/move")
async def move_lead_in_pipeline(client_id: str, new_stage: str, current_admin=Depends(verify_token)):
    """Update client pipeline stage and log the activity."""
    db = get_db()
    admin_id = current_admin["sub"]
    
    # Update stage
    await db_execute(lambda: db.table("clients").update({
        "pipeline_stage": new_stage, 
        "updated_at": datetime.now().isoformat()
    }).eq("id", client_id).execute())
    
    # Log activity
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "pipeline_move",
        "description": f"Lead moved to {new_stage} stage",
        "client_id": client_id,
        "performed_by": admin_id,
        "created_at": datetime.now().isoformat()
    }).execute())
    
    return {"status": "success"}

@router.patch("/clients/{client_id}")
async def update_client_details(client_id: str, data: dict, current_admin=Depends(verify_token)):
    """Allow sales reps to edit lead data and log the changes."""
    db = get_db()
    admin_id = current_admin["sub"]
    
    # Exclude restricted fields
    update_data = {k: v for k, v in data.items() if k not in ["id", "created_at", "assigned_rep_id"]}
    update_data["updated_at"] = datetime.now().isoformat()
    
    res = await db_execute(lambda: db.table("clients").update(update_data).eq("id", client_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Log activity
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "client_edit",
        "description": f"Updated client information: {', '.join(update_data.keys())}",
        "client_id": client_id,
        "performed_by": admin_id,
        "created_at": datetime.now().isoformat()
    }).execute())
    
    return res.data[0]


# ============================================================
# CLIENT NOTES & INTERACTIONS
# ============================================================

@router.post("/contacts/{client_id}/notes")
async def add_client_note(
    client_id: str,
    request: Request,
    current_admin=Depends(verify_token)
):
    """Add a note to a client"""
    db = get_db()
    body = await request.json()
    
    note = body.get("note", "").strip()
    if not note:
        raise HTTPException(status_code=400, detail="Note cannot be empty")
    
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "client_note",
        "description": note,
        "client_id": client_id,
        "performed_by": current_admin["sub"],
        "metadata": {"note_type": "manual"}
    }).execute())
    
    return {"status": "note_added"}


@router.post("/contacts/{client_id}/call")
async def log_call(
    client_id: str,
    request: Request,
    current_admin=Depends(verify_token)
):
    """Log a call with a client"""
    db = get_db()
    body = await request.json()
    
    duration = body.get("duration", 0)  # in minutes
    notes = body.get("notes", "")
    
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "call",
        "description": f"Call logged: {notes}",
        "client_id": client_id,
        "performed_by": current_admin["sub"],
        "metadata": {"duration_minutes": duration, "notes": notes}
    }).execute())
    
    return {"status": "call_logged"}


@router.post("/contacts/{client_id}/send-email")
async def send_email_to_contact(
    client_id: str,
    request: Request,
    current_admin=Depends(verify_token)
):
    """Log email sent to client"""
    db = get_db()
    body = await request.json()
    
    subject = body.get("subject", "")
    message = body.get("message", "")
    
    # Get client email
    client_res = await db_execute(lambda: db.table("clients").select("email").eq("id", client_id).execute())
    if not client_res.data:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Log in activity
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "email",
        "description": f"Email sent: {subject}",
        "client_id": client_id,
        "performed_by": current_admin["sub"],
        "metadata": {"subject": subject, "message": message}
    }).execute())
    
    return {"status": "email_logged"}


# ============================================================
# CRM ANALYTICS
# ============================================================

@router.get("/analytics/pipeline-health")
async def get_pipeline_health(current_admin=Depends(verify_token)):
    """Pipeline health metrics"""
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])
    
    # 1. Base Query
    query = db.table("invoices").select("""
        id, amount, amount_paid, status, due_date, created_at, clients(assigned_rep_id)
    """)
    
    if not is_privileged:
        # Join check: filter where the client's assigned rep is the current user
        query = query.filter("clients.assigned_rep_id", "eq", admin_id)
    
    res = await db_execute(lambda: query.neq("status", "voided").execute())
    all_invoices = res.data or []
    
    today = datetime.now().date()
    
    metrics = {
        "total_value": sum(float(i["amount"]) for i in all_invoices),
        "total_collected": sum(float(i["amount_paid"]) for i in all_invoices),
        "total_outstanding": sum(float(i["amount"]) - float(i["amount_paid"]) for i in all_invoices),
        "total_deals": len(all_invoices),
        "won_deals": len([i for i in all_invoices if i["status"] == "paid"]),
        "open_deals": len([i for i in all_invoices if i["status"] in ["unpaid", "partial"]]),
        "overdue_deals": len([i for i in all_invoices if i["status"] == "overdue"]),
        "avg_deal_size": 0,
        "win_rate": 0,
        "at_risk_deals": 0
    }
    
    if metrics["total_deals"] > 0:
        metrics["avg_deal_size"] = metrics["total_value"] / metrics["total_deals"]
        metrics["win_rate"] = (metrics["won_deals"] / metrics["total_deals"]) * 100
    
    # At-risk deals (unpaid & overdue)
    metrics["at_risk_deals"] = metrics["overdue_deals"] + len([
        i for i in all_invoices 
        if i["status"] in ["unpaid", "partial"] 
        and str(i.get("due_date", "9999-01-01")) < str(today)
    ])
    
    return metrics


@router.get("/analytics/sales-rep-performance")
async def get_sales_rep_performance(current_admin=Depends(verify_token)):
    """Sales rep performance metrics"""
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])
    
    query = db.table("invoices").select("""
        id, sales_rep_name, amount, amount_paid, status, created_at, clients(assigned_rep_id)
    """)
    
    if not is_privileged:
        query = query.filter("clients.assigned_rep_id", "eq", admin_id)
        
    res = await db_execute(lambda: query.neq("status", "voided").execute())
    invoices = res.data or []
    
    # Group by sales rep
    reps = {}
    for inv in invoices:
        rep_name = inv.get("sales_rep_name") or "Unassigned"
        if rep_name not in reps:
            reps[rep_name] = {
                "total_deals": 0,
                "total_value": 0,
                "total_collected": 0,
                "closed_deals": 0
            }
        
        reps[rep_name]["total_deals"] += 1
        reps[rep_name]["total_value"] += float(inv["amount"])
        reps[rep_name]["total_collected"] += float(inv["amount_paid"])
        if inv["status"] == "paid":
            reps[rep_name]["closed_deals"] += 1
    
    # Calculate conversion rates
    rep_performance = []
    for rep_name, stats in reps.items():
        conversion_rate = (stats["closed_deals"] / stats["total_deals"] * 100) if stats["total_deals"] > 0 else 0
        rep_performance.append({
            "name": rep_name,
            "total_deals": stats["total_deals"],
            "total_value": stats["total_value"],
            "total_collected": stats["total_collected"],
            "closed_deals": stats["closed_deals"],
            "conversion_rate": round(conversion_rate, 1),
            "avg_deal_size": stats["total_value"] / stats["total_deals"] if stats["total_deals"] > 0 else 0
        })
    
    # Sort by total value
    rep_performance.sort(key=lambda x: x["total_value"], reverse=True)
    
    return rep_performance


@router.get("/analytics/client-insights")
async def get_client_insights(current_admin=Depends(verify_token)):
    """Client lifetime value and engagement insights (BULK OPTIMIZED)"""
    db = get_db()
    
    clients = (await db_execute(lambda: db.table("clients").select("id, full_name, email, created_at").execute())).data or []
    if not clients:
        return []

    client_ids = [c["id"] for c in clients]
    
    # BULK FETCH: Invoices and Activities ✅
    all_invoices = (await db_execute(lambda: db.table("invoices")\
        .select("id, client_id, amount, amount_paid, status")\
        .in_("client_id", client_ids)\
        .execute())).data or []
        
    all_activities = (await db_execute(lambda: db.table("activity_log")\
        .select("id, client_id, event_type, created_at")\
        .in_("client_id", client_ids)\
        .execute())).data or []
        
    # Indexing
    inv_map = {}
    for i in all_invoices:
        cid = i["client_id"]
        if cid not in inv_map: inv_map[cid] = []
        inv_map[cid].append(i)
        
    act_map = {}
    for a in all_activities:
        cid = a["client_id"]
        if cid not in act_map: act_map[cid] = []
        act_map[cid].append(a)
    
    insights = []
    for client in clients:
        cid = client["id"]
        invoices = inv_map.get(cid, [])
        activities = act_map.get(cid, [])
        
        if invoices or activities:
            ltv = sum(float(i["amount"]) for i in invoices)
            collected = sum(float(i["amount_paid"]) for i in invoices)
            
            activity_dates = [a.get("created_at") for a in activities]
            last_interaction = max(activity_dates + [client.get("created_at")]) if activity_dates else client.get("created_at")
            
            insights.append({
                "client_id": cid,
                "client_name": client["full_name"],
                "lifetime_value": ltv,
                "amount_collected": collected,
                "total_deals": len(invoices),
                "engagement_score": min(100, len(activities) * 5),
                "last_interaction": last_interaction,
                "potential_churn_risk": any(i["status"] == "overdue" for i in invoices)
            })
    
    return sorted(insights, key=lambda x: x["lifetime_value"], reverse=True)


# ============================================================
# ACTIVITY TIMELINE
# ============================================================

@router.get("/activities")
async def get_recent_activities(
    limit: int = 50,
    current_admin=Depends(verify_token)
):
    """Get recent CRM activities"""
    db = get_db()
    
    activities = (await db_execute(lambda: db.table("activity_log").select("""
        id, event_type, description, client_id, invoice_id, performed_by, created_at
    """).order("created_at", desc=True).limit(limit).execute())).data or []
    
    # Enrich with client names (BULK FETCH recommended, but using loop with db_execute for stability if list is small)
    for activity in activities:
        if activity.get("client_id"):
            client_res = await db_execute(lambda: db.table("clients").select("full_name").eq("id", activity["client_id"]).execute())
            if client_res.data:
                activity["client_name"] = client_res.data[0]["full_name"]
    
    return activities


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@router.get("/dashboard")
async def get_crm_dashboard_summary(current_admin=Depends(verify_token)):
    """Get complete CRM dashboard summary"""
    db = get_db()
    
    # Pipeline health
    pipeline = await get_sales_pipeline(current_admin)
    health = await get_pipeline_health(current_admin)
    stats = await get_sales_rep_performance(current_admin)
    
    # Recent activities
    activities = (await db_execute(lambda: db.table("activity_log")\
        .select("id, event_type, description, client_id, created_at")\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute())).data or []
    
    # Upcoming tasks (using overdue + upcoming invoices)
    upcoming = (await db_execute(lambda: db.table("invoices")\
        .select("id, invoice_number, due_date, client_id, amount")\
        .gte("due_date", datetime.now().date().isoformat())\
        .lte("due_date", (datetime.now().date() + timedelta(days=7)).isoformat())\
        .execute())).data or []
    
    return {
        "health": health,
        "pipeline": pipeline,
        "top_performers": stats[:5] if stats else [],
        "recent_activities": activities,
        "upcoming_deliverables": upcoming
    }

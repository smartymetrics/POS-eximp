from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from database import get_db
from routers.auth import verify_token, require_roles
from datetime import datetime, timedelta
import json

router = APIRouter()

# ============================================================
# CRM CONTACT & CLIENT MANAGEMENT
# ============================================================

@router.get("/contacts")
async def get_all_contacts(current_admin=Depends(verify_token)):
    """Get all clients with their invoice & payment summary"""
    db = get_db()
    
    contacts = db.table("clients").select("""
        id, 
        full_name, 
        email, 
        phone,
        city,
        state,
        occupation,
        created_at,
        updated_at
    """).order("created_at", desc=True).execute().data
    
    # Enrich each contact with sales data
    enriched = []
    for contact in contacts:
        invoices = db.table("invoices")\
            .select("id, amount, amount_paid, status, invoice_date, due_date")\
            .eq("client_id", contact["id"])\
            .execute().data or []
        
        total_value = sum(float(i["amount"]) for i in invoices)
        total_paid = sum(float(i["amount_paid"]) for i in invoices)
        unpaid_count = len([i for i in invoices if i["status"] in ["unpaid", "partial", "overdue"]])
        
        contact["total_value"] = total_value
        contact["amount_paid"] = total_paid
        contact["balance"] = total_value - total_paid
        contact["unpaid_deals"] = unpaid_count
        contact["total_deals"] = len(invoices)
        
        enriched.append(contact)
    
    return enriched


@router.get("/contacts/{client_id}")
async def get_contact_details(client_id: str, current_admin=Depends(verify_token)):
    """Get complete client profile with all interactions"""
    db = get_db()
    
    # Get client
    client_result = db.table("clients").select("*").eq("id", client_id).execute()
    if not client_result.data:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client = client_result.data[0]
    
    # Get all invoices/deals
    invoices = db.table("invoices").select("""
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
    """).eq("client_id", client_id).order("invoice_date", desc=True).execute().data or []
    
    # Get all payments
    payments = db.table("payments").select("""
        id,
        amount,
        payment_method,
        reference,
        payment_date,
        notes,
        created_at
    """).eq("client_id", client_id).order("payment_date", desc=True).execute().data or []
    
    # Get all activities
    activities = db.table("activity_log").select("""
        id,
        event_type,
        description,
        performed_by,
        created_at,
        metadata
    """).eq("client_id", client_id).order("created_at", desc=True).limit(50).execute().data or []
    
    # Get email logs
    emails = db.table("email_logs").select("""
        id,
        email_type,
        recipient_email,
        subject,
        status,
        sent_at
    """).eq("client_id", client_id).order("sent_at", desc=True).limit(20).execute().data or []
    
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
    Get all invoices grouped by Sales Stage (pipeline stages)
    🔥 PERFORMANCE OPTIMIZED: Fetches all stages and client details in bulk.
    """
    db = get_db()
    
    # 1. Fetch ALL pipeline invoices with client details in ONE query using foreign key join
    # This replaces the 4-loop + nested client loop (N+1)
    result = db.table("invoices").select("""
        id,
        invoice_number,
        amount,
        amount_paid,
        status,
        pipeline_stage,
        due_date,
        client_id,
        sales_rep_name,
        created_at,
        clients (
            full_name,
            email
        )
    """).neq("pipeline_stage", "").order("created_at", desc=True).execute()
    
    all_invoices = result.data or []
    
    # 2. Group by stage in-memory
    stages = ["inspection", "offer", "contract", "closed"]
    pipeline = {stage: {"deals": [], "count": 0, "total_value": 0, "total_paid": 0} for stage in stages}
    
    for inv in all_invoices:
        stage = inv.get("pipeline_stage")
        if stage in pipeline:
            # Flatten client data for frontend
            client_data = inv.get("clients") or {}
            inv["client_name"] = client_data.get("full_name", "Unknown Client")
            inv["client_email"] = client_data.get("email", "N/A")
            
            pipeline[stage]["deals"].append(inv)
            pipeline[stage]["count"] += 1
            pipeline[stage]["total_value"] += float(inv.get("amount") or 0)
            pipeline[stage]["total_paid"] += float(inv.get("amount_paid") or 0)
    
    return pipeline


@router.put("/pipeline/{invoice_id}/move")
async def move_deal_in_pipeline(
    invoice_id: str,
    new_stage: str,
    current_admin=Depends(verify_token)
):
    """Update invoice pipeline stage"""
    db = get_db()
    
    valid_stages = ["inspection", "offer", "contract", "closed"]
    if new_stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of {valid_stages}")
    
    # Update invoice
    result = db.table("invoices")\
        .update({"pipeline_stage": new_stage, "updated_at": datetime.now().isoformat()})\
        .eq("id", invoice_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Log activity
    invoice = result.data[0]
    db.table("activity_log").insert({
        "event_type": "pipeline_move",
        "description": f"Deal moved to {new_stage} stage",
        "client_id": invoice["client_id"],
        "invoice_id": invoice_id,
        "performed_by": current_admin["sub"],
        "metadata": {"new_stage": new_stage}
    }).execute()
    
    return {"status": "updated", "new_stage": new_stage}


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
    
    db.table("activity_log").insert({
        "event_type": "client_note",
        "description": note,
        "client_id": client_id,
        "performed_by": current_admin["sub"],
        "metadata": {"note_type": "manual"}
    }).execute()
    
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
    
    db.table("activity_log").insert({
        "event_type": "call",
        "description": f"Call logged: {notes}",
        "client_id": client_id,
        "performed_by": current_admin["sub"],
        "metadata": {"duration_minutes": duration, "notes": notes}
    }).execute()
    
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
    client = db.table("clients").select("email").eq("id", client_id).execute()
    if not client.data:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Log in activity
    db.table("activity_log").insert({
        "event_type": "email",
        "description": f"Email sent: {subject}",
        "client_id": client_id,
        "performed_by": current_admin["sub"],
        "metadata": {"subject": subject, "message": message}
    }).execute()
    
    return {"status": "email_logged"}


# ============================================================
# CRM ANALYTICS
# ============================================================

@router.get("/analytics/pipeline-health")
async def get_pipeline_health(current_admin=Depends(verify_token)):
    """Pipeline health metrics"""
    db = get_db()
    
    # Get all invoices
    all_invoices = db.table("invoices").select("""
        id, amount, amount_paid, status, due_date, created_at
    """).execute().data or []
    
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
    
    invoices = db.table("invoices").select("""
        id, sales_rep_name, amount, amount_paid, status, created_at
    """).execute().data or []
    
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
    """Client lifetime value and engagement insights"""
    db = get_db()
    
    clients = db.table("clients").select("id, full_name, email, created_at").execute().data or []
    
    insights = []
    for client in clients:
        # Get invoices
        invoices = db.table("invoices")\
            .select("id, amount, amount_paid, status, created_at")\
            .eq("client_id", client["id"])\
            .execute().data or []
        
        # Get activities
        activities = db.table("activity_log")\
            .select("id, event_type, created_at")\
            .eq("client_id", client["id"])\
            .execute().data or []
        
        if invoices or activities:
            ltv = sum(float(i["amount"]) for i in invoices)
            collected = sum(float(i["amount_paid"]) for i in invoices)
            
            insights.append({
                "client_id": client["id"],
                "client_name": client["full_name"],
                "lifetime_value": ltv,
                "amount_collected": collected,
                "total_deals": len(invoices),
                "engagement_score": min(100, len(activities) * 5),  # Simple engagement metric
                "last_interaction": max([a.get("created_at") for a in activities] + [client.get("created_at")]),
                "potential_churn_risk": len([i for i in invoices if i["status"] == "overdue"]) > 0
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
    
    activities = db.table("activity_log").select("""
        id,
        event_type,
        description,
        client_id,
        invoice_id,
        performed_by,
        created_at
    """).order("created_at", desc=True).limit(limit).execute().data or []
    
    # Enrich with client names
    for activity in activities:
        if activity.get("client_id"):
            client = db.table("clients").select("full_name").eq("id", activity["client_id"]).execute()
            if client.data:
                activity["client_name"] = client.data[0]["full_name"]
    
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
    activities = db.table("activity_log")\
        .select("id, event_type, description, client_id, created_at")\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute().data or []
    
    # Upcoming tasks (using overdue + upcoming invoices)
    upcoming = db.table("invoices")\
        .select("id, invoice_number, due_date, client_id, amount")\
        .gte("due_date", datetime.now().date().isoformat())\
        .lte("due_date", (datetime.now().date() + timedelta(days=7)).isoformat())\
        .execute().data or []
    
    return {
        "health": health,
        "pipeline": pipeline,
        "top_performers": stats[:5] if stats else [],
        "recent_activities": activities,
        "upcoming_deliverables": upcoming
    }

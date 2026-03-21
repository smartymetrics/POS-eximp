from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, date, timedelta
from database import get_db
from routers.auth import verify_token
from models import (
    KPISummary, KPIDelta, RevenueTrend, EstateStat, 
    PaymentStatusStats, ReferralSourceStat, RepLeaderboardEntry, ActivityLogEntry
)

router = APIRouter()

def get_previous_period(start: date, end: date):
    delta = end - start
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - delta
    return prev_start, prev_end

@router.get("/kpis", response_model=KPISummary)
async def get_kpis(
    start: date = Query(...),
    end: date = Query(...),
    admin: dict = Depends(verify_token)
):
    db = get_db()
    is_admin = admin.get("role") == "admin"
    
    # 1. Total Invoiced (Revenue)
    invoiced_query = db.table("invoices").select("amount").filter("invoice_date", "gte", start.isoformat()).filter("invoice_date", "lte", end.isoformat())
    invoiced_data = invoiced_query.execute().data
    total_revenue = sum(float(i["amount"]) for i in invoiced_data) if is_admin else None
    plots_sold = len(invoiced_data)
    
    # 2. Amount Collected
    collected_query = db.table("payments").select("amount").filter("payment_date", "gte", start.isoformat()).filter("payment_date", "lte", end.isoformat()).eq("is_voided", False)
    collected_data = collected_query.execute().data
    amount_collected = sum(float(p["amount"]) for p in collected_data) if is_admin else None
    
    # 3. New Clients
    clients_query = db.table("clients").select("id", count="exact").filter("created_at", "gte", start.isoformat()).filter("created_at", "lte", end.isoformat() + "T23:59:59")
    new_clients = clients_query.execute().count
    
    # 4. Pending Verifications (Always live)
    pending_count = db.table("pending_verifications").select("id", count="exact").eq("status", "pending").execute().count
    
    # Outstanding & Rate
    outstanding = (total_revenue - amount_collected) if is_admin and total_revenue is not None else None
    collection_rate = (amount_collected / total_revenue * 100) if is_admin and total_revenue and total_revenue > 0 else 0
    avg_deal = (total_revenue / plots_sold) if is_admin and plots_sold > 0 else 0
    
    # Delta Logic (Simplified)
    delta = None
    if is_admin:
        prev_start, prev_end = get_previous_period(start, end)
        # Prev Revenue
        prev_rev_data = db.table("invoices").select("amount").filter("invoice_date", "gte", prev_start.isoformat()).filter("invoice_date", "lte", prev_end.isoformat()).execute().data
        prev_revenue = sum(float(i["amount"]) for i in prev_rev_data)
        
        # Prev Collected
        prev_col_data = db.table("payments").select("amount").filter("payment_date", "gte", prev_start.isoformat()).filter("payment_date", "lte", prev_end.isoformat()).eq("is_voided", False).execute().data
        prev_collected = sum(float(p["amount"]) for p in prev_col_data)
        
        # Prev Clients
        prev_clients = db.table("clients").select("id", count="exact").filter("created_at", "gte", prev_start.isoformat()).filter("created_at", "lte", prev_end.isoformat() + "T23:59:59").execute().count
        
        delta = KPIDelta(
            total_revenue=((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else None,
            amount_collected=((amount_collected - prev_collected) / prev_collected * 100) if prev_collected > 0 else None,
            new_clients=((new_clients - prev_clients) / prev_clients * 100) if prev_clients > 0 else None
        )

    return KPISummary(
        total_revenue=total_revenue,
        amount_collected=amount_collected,
        outstanding_balance=outstanding,
        new_clients=new_clients,
        plots_sold=plots_sold,
        avg_deal_size=avg_deal,
        collection_rate=collection_rate,
        pending_verifications=pending_count,
        delta=delta
    )

@router.get("/revenue-trend", response_model=RevenueTrend)
async def get_revenue_trend(
    start: date = Query(...),
    end: date = Query(...),
    granularity: str = "daily",
    admin: dict = Depends(verify_token)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Financial data restricted to admins")
        
    db = get_db()
    # Fetch all invoices and payments in period
    invoices = db.table("invoices").select("amount", "invoice_date").filter("invoice_date", "gte", start.isoformat()).filter("invoice_date", "lte", end.isoformat()).execute().data
    payments = db.table("payments").select("amount", "payment_date").filter("payment_date", "gte", start.isoformat()).filter("payment_date", "lte", end.isoformat()).eq("is_voided", False).execute().data
    
    # Aggregate by date
    labels = []
    invoiced_vals = []
    collected_vals = []
    
    curr = start
    while curr <= end:
        date_str = curr.isoformat()
        labels.append(curr.strftime("%b %d"))
        
        inv_sum = sum(float(i["amount"]) for i in invoices if i["invoice_date"] == date_str)
        col_sum = sum(float(p["amount"]) for p in payments if p["payment_date"] == date_str)
        
        invoiced_vals.append(inv_sum)
        collected_vals.append(col_sum)
        curr += timedelta(days=1)
        
    return RevenueTrend(labels=labels, invoiced=invoiced_vals, collected=collected_vals)

@router.get("/estates", response_model=List[EstateStat])
async def get_estates(
    start: date = Query(...),
    end: date = Query(...),
    admin: dict = Depends(verify_token)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Restricted")
        
    db = get_db()
    data = db.table("invoices").select("property_name", "amount").filter("invoice_date", "gte", start.isoformat()).filter("invoice_date", "lte", end.isoformat()).execute().data
    
    stats = {}
    for item in data:
        name = item["property_name"] or "Unknown"
        if name not in stats:
            stats[name] = {"revenue": 0, "deals": 0}
        stats[name]["revenue"] += float(item["amount"])
        stats[name]["deals"] += 1
        
    return [EstateStat(name=k, revenue=v["revenue"], deals=v["deals"]) for k, v in stats.items()]

@router.get("/payment-status", response_model=PaymentStatusStats)
async def get_payment_status(
    start: date = Query(...),
    end: date = Query(...),
    admin: dict = Depends(verify_token)
):
    db = get_db()
    data = db.table("invoices").select("status").filter("invoice_date", "gte", start.isoformat()).filter("invoice_date", "lte", end.isoformat()).execute().data
    
    return PaymentStatusStats(
        paid=len([i for i in data if i["status"] == "paid"]),
        partial=len([i for i in data if i["status"] == "partial"]),
        unpaid=len([i for i in data if i["status"] == "unpaid"])
    )

@router.get("/referral-sources", response_model=List[ReferralSourceStat])
async def get_referral_sources(
    start: date = Query(...),
    end: date = Query(...),
    admin: dict = Depends(verify_token)
):
    db = get_db()
    data = db.table("clients").select("referral_source").filter("created_at", "gte", start.isoformat()).filter("created_at", "lte", end.isoformat() + "T23:59:59").execute().data
    
    sources = {}
    for item in data:
        s = item["referral_source"] or "Other"
        sources[s] = sources.get(s, 0) + 1
        
    return [ReferralSourceStat(source=k, count=v) for k, v in sources.items()]

@router.get("/activity", response_model=List[ActivityLogEntry])
async def get_activity(
    limit: int = 20,
    offset: int = 0,
    admin: dict = Depends(verify_token)
):
    db = get_db()
    # Join with admins to get perforemed_by name
    data = db.table("activity_log")\
        .select("*, admins(full_name)")\
        .order("created_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute().data
        
    activity = []
    for item in data:
        activity.append(ActivityLogEntry(
            id=str(item["id"]),
            event_type=item["event_type"],
            description=item["description"],
            client_id=str(item["client_id"]) if item["client_id"] else None,
            invoice_id=str(item["invoice_id"]) if item["invoice_id"] else None,
            performed_by_name=item["admins"].get("full_name") if item.get("admins") else "System",
            created_at=item["created_at"]
        ))
        
    return activity
@router.get("/rep-leaderboard", response_model=List[RepLeaderboardEntry])
async def get_rep_leaderboard(
    start: date = Query(...),
    end: date = Query(...),
    limit: int = 10,
    admin: dict = Depends(verify_token)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Restricted")
        
    db = get_db()
    data = db.table("invoices")\
        .select("sales_rep_name, amount, amount_paid, property_name")\
        .filter("invoice_date", "gte", start.isoformat())\
        .filter("invoice_date", "lte", end.isoformat())\
        .execute().data
        
    reps = {}
    for item in data:
        name = item["sales_rep_name"] or "Unknown"
        if name not in reps:
            reps[name] = {"deals": 0, "total_value": 0, "collected": 0, "estates": {}}
        reps[name]["deals"] += 1
        reps[name]["total_value"] += float(item["amount"])
        reps[name]["collected"] += float(item["amount_paid"])
        
        estate = item["property_name"] or "N/A"
        reps[name]["estates"][estate] = reps[name]["estates"].get(estate, 0) + 1
        
    results = []
    for name, stats in reps.items():
        # Find top estate
        top_estate = max(stats["estates"].items(), key=lambda x: x[1])[0] if stats["estates"] else "N/A"
        
        results.append(RepLeaderboardEntry(
            rep_name=name,
            deals=stats["deals"],
            total_value=stats["total_value"],
            avg_deal_size=stats["total_value"] / stats["deals"],
            top_estate=top_estate,
            collected=stats["collected"],
            collection_rate=(stats["collected"] / stats["total_value"] * 100) if stats["total_value"] > 0 else 0
        ))
        
    # Sort by total value
    results.sort(key=lambda x: x.total_value, reverse=True)
    return results[:limit]

async def log_activity(
    event_type: str,
    description: str,
    performed_by: str,
    client_id: Optional[str] = None,
    invoice_id: Optional[str] = None,
    metadata: Optional[dict] = None
):
    try:
        db = get_db()
        db.table("activity_log").insert({
            "event_type": event_type,
            "description": description,
            "performed_by": performed_by,
            "client_id": client_id,
            "invoice_id": invoice_id,
            "metadata": metadata
        }).execute()
    except Exception as e:
        print(f"Error logging activity: {e}")

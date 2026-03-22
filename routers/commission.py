from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional
from datetime import date, datetime, timedelta
from collections import defaultdict

from models import CommissionRateCreate, CommissionAdjustment, CommissionPayout, DefaultRateUpdate
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity

router = APIRouter()

@router.get("/default-rate")
async def get_default_rate(current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("system_settings").select("*").eq("key", "default_commission_rate").execute()
    return {"rate": res.data[0]["value"] if res.data else "5.00"}

@router.patch("/default-rate")
async def update_default_rate(payload: DefaultRateUpdate, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db = get_db()
    db.table("system_settings").upsert({
        "key": "default_commission_rate",
        "value": str(payload.rate),
        "updated_by": current_admin["sub"],
        "updated_at": datetime.now().isoformat()
    }).execute()
    
    background_tasks.add_task(
        log_activity,
        "commission_default_rate_updated",
        f"Updated default commission rate to {payload.rate}%",
        performed_by=current_admin["sub"]
    )
    return {"message": "Default rate updated", "rate": str(payload.rate)}

@router.get("/rates/{rep_id}")
async def get_rep_rates(rep_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("commission_rates").select("*, admins:set_by(full_name)").eq("sales_rep_id", rep_id).order("effective_from", desc=True).execute()
    return res.data

@router.post("/rates")
async def set_rep_rate(payload: CommissionRateCreate, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db = get_db()
    
    # 1. Deactivate current active rate for this estate
    active_rates = db.table("commission_rates")\
        .select("*")\
        .eq("sales_rep_id", payload.sales_rep_id)\
        .eq("estate_name", payload.estate_name)\
        .is_("effective_to", "null")\
        .execute()
        
    if active_rates.data:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        db.table("commission_rates").update({
            "effective_to": yesterday
        }).eq("id", active_rates.data[0]["id"]).execute()
        
    # 2. Insert new rate
    new_rate = db.table("commission_rates").insert({
        "sales_rep_id": payload.sales_rep_id,
        "estate_name": payload.estate_name,
        "rate": float(payload.rate),
        "effective_from": payload.effective_from.isoformat(),
        "reason": payload.reason,
        "set_by": current_admin["sub"]
    }).execute()

    return new_rate.data[0]

@router.get("/earnings")
async def list_earnings(rep_id: Optional[str] = None, is_paid: Optional[bool] = None, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("commission_earnings").select("*, sales_reps(name), clients(full_name), invoices(invoice_number)").order("created_at", desc=True)
    if rep_id:
        query = query.eq("sales_rep_id", rep_id)
    if is_paid is not None:
        query = query.eq("is_paid", is_paid)
    res = query.execute()
    return res.data

@router.get("/earnings/rep/{rep_id}")
async def rep_earnings(rep_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("commission_earnings").select("*, clients(full_name), invoices(invoice_number)").eq("sales_rep_id", rep_id).order("created_at", desc=True).execute()
    return res.data

@router.patch("/earnings/{id}/adjust")
async def adjust_earnings(id: str, payload: CommissionAdjustment, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db = get_db()
    
    old_rec = db.table("commission_earnings").select("*").eq("id", id).execute()
    if not old_rec.data:
        raise HTTPException(status_code=404, detail="Earning record not found")
        
    rec = old_rec.data[0]
    
    if len(payload.adjustment_reason) < 10:
        raise HTTPException(status_code=400, detail="Reason must be descriptive")
        
    res = db.table("commission_earnings").update({
        "adjusted_amount": float(payload.adjusted_amount),
        "adjustment_reason": payload.adjustment_reason,
        "adjusted_by": current_admin["sub"],
        "adjusted_at": datetime.now().isoformat()
    }).eq("id", id).execute()
    
    background_tasks.add_task(
        log_activity,
        "commission_adjusted",
        f"Commission for invoice {rec['invoice_id']} adjusted from {rec.get('final_amount', rec['commission_amount'])} to {payload.adjusted_amount}. Reason: {payload.adjustment_reason}",
        performed_by=current_admin["sub"]
    )
    
    return res.data[0]

@router.get("/owed")
async def summary_owed(current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("commission_earnings").select("*, sales_reps(name)").eq("is_paid", False).execute()
    
    owed = defaultdict(lambda: {"total": 0.0, "count": 0, "name": ""})
    for e in res.data:
        rep_id = e["sales_rep_id"]
        owed[rep_id]["name"] = e["sales_reps"]["name"] if e.get("sales_reps") else "Unknown"
        owed[rep_id]["total"] += float(e["final_amount"])
        owed[rep_id]["count"] += 1
        
    result = [{"rep_id": k, **v} for k, v in owed.items()]
    return sorted(result, key=lambda x: x["total"], reverse=True)

@router.get("/owed/{rep_id}")
async def detailed_owed(rep_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("commission_earnings").select("*, clients(full_name), invoices(invoice_number)").eq("sales_rep_id", rep_id).eq("is_paid", False).order("created_at", desc=True).execute()
    return res.data

@router.post("/payout")
async def mark_payout(payload: CommissionPayout, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db = get_db()
    if not payload.earning_ids:
        raise HTTPException(status_code=400, detail="No earnings selected")
        
    earnings_query = db.table("commission_earnings").select("final_amount, is_paid").in_("id", payload.earning_ids).eq("sales_rep_id", payload.sales_rep_id).execute()
    amount = sum(float(e["final_amount"]) for e in earnings_query.data if not e["is_paid"])
    
    if amount == 0:
        raise HTTPException(status_code=400, detail="Selected earnings are already paid or totally amount to 0")

    batch = db.table("payout_batches").insert({
        "sales_rep_id": payload.sales_rep_id,
        "total_amount": amount,
        "reference": payload.reference,
        "notes": payload.notes,
        "paid_by": current_admin["sub"]
    }).execute()
    
    batch_id = batch.data[0]["id"]
    
    db.table("commission_earnings").update({
        "is_paid": True,
        "paid_at": datetime.now().isoformat(),
        "paid_by": current_admin["sub"],
        "payout_reference": payload.reference,
        "payout_batch_id": batch_id
    }).in_("id", payload.earning_ids).execute()
    
    rep_res = db.table("sales_reps").select("name").eq("id", payload.sales_rep_id).execute()
    rep_name = rep_res.data[0]["name"] if rep_res.data else "Rep"
    
    background_tasks.add_task(
        log_activity,
        "commission_payout",
        f"Processed commission payout of NGN {amount:,.2f} to {rep_name}",
        performed_by=current_admin["sub"]
    )
    
    return {"message": "Payout successful", "batch": batch.data[0]}

@router.get("/payouts")
async def list_payouts(rep_id: Optional[str] = None, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("payout_batches").select("*, sales_reps(name), admins:paid_by(full_name)").order("paid_at", desc=True)
    if rep_id:
        query = query.eq("sales_rep_id", rep_id)
    res = query.execute()
    return res.data

@router.get("/payouts/rep/{rep_id}")
async def rep_payouts(rep_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("payout_batches").select("*, admins:paid_by(full_name)").eq("sales_rep_id", rep_id).order("paid_at", desc=True).execute()
    return res.data

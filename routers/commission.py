from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional
from datetime import date, datetime, timedelta
from collections import defaultdict

from models import CommissionRateCreate, CommissionAdjustment, CommissionPayout, DefaultRateUpdate, CommissionVoidRequest
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from email_service import send_commission_void_email, send_commission_paid_email

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
    query = db.table("commission_earnings").select("*, sales_reps(name), clients(full_name), invoices(invoice_number)").eq("is_voided", False).order("created_at", desc=True)
    if rep_id:
        query = query.eq("sales_rep_id", rep_id)
    if is_paid is not None:
        query = query.eq("is_paid", is_paid)
    res = query.execute()
    return res.data

@router.get("/earnings/rep/{rep_id}")
async def rep_earnings(rep_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("commission_earnings").select("*, clients(full_name), invoices(invoice_number)").eq("sales_rep_id", rep_id).eq("is_voided", False).order("created_at", desc=True).execute()
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
    res = db.table("commission_earnings").select("*, sales_reps(name)").eq("is_paid", False).eq("is_voided", False).execute()
    
    owed = defaultdict(lambda: {"total": 0.0, "count": 0, "name": "", "partially_paid": False})
    for e in res.data:
        rep_id = e["sales_rep_id"]
        owed[rep_id]["name"] = e["sales_reps"]["name"] if e.get("sales_reps") else "Unknown"
        # Subtract any partial payments already applied
        amount_paid = float(e.get("amount_paid") or 0)
        balance = float(e["final_amount"]) - amount_paid
        owed[rep_id]["total"] += balance
        owed[rep_id]["count"] += 1
        if amount_paid > 0:
            owed[rep_id]["partially_paid"] = True
        
    result = [{"rep_id": k, **v} for k, v in owed.items()]
    return sorted(result, key=lambda x: x["total"], reverse=True)


@router.get("/owed/{rep_id}")
async def detailed_owed(rep_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    # Include amount_paid so frontend can show balance accurately
    res = db.table("commission_earnings").select("*, clients(full_name), invoices(invoice_number)").eq("sales_rep_id", rep_id).eq("is_paid", False).eq("is_voided", False).order("created_at", desc=True).execute()
    # Annotate each record with the true balance remaining
    for e in res.data:
        e["balance_owed"] = round(float(e["final_amount"]) - float(e.get("amount_paid") or 0), 2)
    return res.data


@router.post("/payout")
async def mark_payout(payload: CommissionPayout, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db = get_db()
    if not payload.earning_ids:
        raise HTTPException(status_code=400, detail="No earnings selected")
    
    # Fetch selected unpaid earnings ordered oldest-first for waterfall
    earnings_query = db.table("commission_earnings")\
        .select("id, final_amount, amount_paid, is_paid")\
        .in_("id", payload.earning_ids)\
        .eq("sales_rep_id", payload.sales_rep_id)\
        .order("created_at", desc=False)\
        .execute()
    
    earnings = [e for e in earnings_query.data if not e["is_paid"]]
    
    if not earnings:
        raise HTTPException(status_code=400, detail="Selected earnings are already paid or total 0")
    
    total_owed = sum(float(e["final_amount"]) - float(e.get("amount_paid") or 0) for e in earnings)
    
    # If no specific amount given, pay everything in full
    payment_amount = float(payload.total_amount) if payload.total_amount else total_owed
    
    if payment_amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")
    if payment_amount > total_owed:
        raise HTTPException(status_code=400, detail=f"Payment amount exceeds total owed (NGN {total_owed:,.2f})")

    # Create payout batch record
    batch = db.table("payout_batches").insert({
        "sales_rep_id": payload.sales_rep_id,
        "total_amount": payment_amount,
        "reference": payload.reference,
        "notes": payload.notes,
        "paid_by": current_admin["sub"]
    }).execute()
    batch_id = batch.data[0]["id"]
    
    # --- Waterfall Distribution ---
    remaining = payment_amount
    for earning in earnings:
        if remaining <= 0:
            break
        
        already_paid = float(earning.get("amount_paid") or 0)
        balance = float(earning["final_amount"]) - already_paid
        to_apply = min(remaining, balance)
        new_amount_paid = already_paid + to_apply
        is_now_fully_paid = round(new_amount_paid, 2) >= round(float(earning["final_amount"]), 2)
        
        update_data = {
            "amount_paid": round(new_amount_paid, 2),
            "payout_batch_id": batch_id,
            "payout_reference": payload.reference,
        }
        if is_now_fully_paid:
            update_data["is_paid"] = True
            update_data["paid_at"] = datetime.now().isoformat()
            update_data["paid_by"] = current_admin["sub"]
        
        db.table("commission_earnings").update(update_data).eq("id", earning["id"]).execute()
        remaining = round(remaining - to_apply, 2)
    
    rep_res = db.table("sales_reps").select("name").eq("id", payload.sales_rep_id).execute()
    rep_name = rep_res.data[0]["name"] if rep_res.data else "Rep"
    
    background_tasks.add_task(
        log_activity,
        "commission_payout",
        f"Processed commission payout of NGN {payment_amount:,.2f} to {rep_name}",
        performed_by=current_admin["sub"]
    )
    
    # Send Payout Email
    rep_obj = db.table("sales_reps").select("*").eq("id", payload.sales_rep_id).single().execute().data
    if rep_obj:
        background_tasks.add_task(send_commission_paid_email, rep_obj, batch.data[0])
    
    return {"message": "Payout successful", "batch": batch.data[0], "amount_paid": payment_amount}


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


@router.post("/earnings/{id}/void")
async def void_earning(id: str, payload: CommissionVoidRequest, background_tasks: BackgroundTasks, current_admin=Depends(verify_token)):
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db = get_db()
    
    # 1. Fetch record
    earning_res = db.table("commission_earnings").select("*, sales_reps(*)").eq("id", id).execute()
    if not earning_res.data:
        raise HTTPException(status_code=404, detail="Earning record not found")
        
    earning = earning_res.data[0]
    if earning["is_paid"]:
        raise HTTPException(status_code=400, detail="Cannot void a paid commission record")
        
    # 2. Void it
    db.table("commission_earnings").update({
        "is_voided": True,
        "voided_at": datetime.now().isoformat(),
        "voided_by": current_admin["sub"],
        "void_reason": payload.reason
    }).eq("id", id).execute()
    
    # 3. Log and email
    background_tasks.add_task(
        log_activity,
        "commission_voided",
        f"Commission of NGN {earning['final_amount']:,.2f} voided. Reason: {payload.reason}",
        performed_by=current_admin["sub"]
    )
    
    # Fetch client and invoice for email context
    inv_res = db.table("invoices").select("*").eq("id", earning["invoice_id"]).execute()
    client_res = db.table("clients").select("*").eq("id", earning["client_id"]).execute()
    
    if inv_res.data and client_res.data:
        background_tasks.add_task(
            send_commission_void_email,
            earning["sales_reps"],
            client_res.data[0],
            inv_res.data[0],
            earning,
            payload.reason
        )
    
    return {"message": "Commission record voided successfully"}

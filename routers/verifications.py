from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from models import VerificationConfirm, VerificationReject, VerificationUpdate
from database import get_db
from routers.auth import verify_token
from email_service import send_receipt_and_statement_email, send_rejection_email, send_commission_earned_email
from routers.analytics import log_activity
from datetime import datetime, date

from commission_service import get_commission_rate
# Re-exported for other modules that depend on it

router = APIRouter()

@router.get("/")
async def list_verifications(current_admin=Depends(verify_token)):
    db = get_db()
    # Fetch pending verifications with client and invoice info
    result = db.table("pending_verifications")\
        .select("*, clients(full_name, email), invoices(invoice_number, property_name, plot_size_sqm, amount, amount_paid, signature_url)")\
        .order("created_at", desc=True)\
        .execute()
    return result.data

@router.get("/count")
async def get_pending_count(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("pending_verifications")\
        .select("id", count="exact")\
        .eq("status", "pending")\
        .execute()
    return {"count": result.count or 0}

@router.patch("/{id}/confirm")
async def confirm_verification(
    id: str, 
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    db = get_db()
    
    # 1. Fetch verification record
    v_res = db.table("pending_verifications").select("*").eq("id", id).execute()
    if not v_res.data:
        raise HTTPException(status_code=404, detail="Verification record not found")
    
    verify_rec = v_res.data[0]
    if verify_rec["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Already {verify_rec['status']}")

    # 2. Update verification status
    update_data = jsonable_encoder({
        "status": "confirmed",
        "reviewed_by": current_admin["sub"],
        "reviewed_at": datetime.now().isoformat()
    })
    db.table("pending_verifications").update(update_data).eq("id", id).execute()

    # 3. Fetch invoice and client for email
    inv_res = db.table("invoices").select("*, clients(*)").eq("id", verify_rec["invoice_id"]).execute()
    invoice = inv_res.data[0]
    client = invoice["clients"]

    # Fetch all invoices for statement
    all_inv = db.table("invoices")\
        .select("*, payments(*)")\
        .eq("client_id", client["id"])\
        .order("invoice_date")\
        .execute()

    rep_id = invoice.get("sales_rep_id")
    rep = None
    if not rep_id and invoice.get("sales_rep_name"):
        # Fallback for old invoices without sales_rep_id
        rep_name = invoice["sales_rep_name"].strip()
        rep_res = db.table("sales_reps")\
            .select("*")\
            .ilike("name", f"%{rep_name}%")\
            .eq("is_active", True)\
            .execute()
        
        if rep_res.data:
            rep = rep_res.data[0]
            rep_id = rep["id"]

    if rep_id and not rep:
        rep_res = db.table("sales_reps").select("*").eq("id", rep_id).execute()
        if rep_res.data:
            rep = rep_res.data[0]
            
    if rep_id:
            # Use the rate logic with fallbacks
            rate = get_commission_rate(
                sales_rep_id=rep_id,
                estate_name=invoice["property_name"],
                verification_date=date.today(),
                db=db
            )
            deposit = float(verify_rec["deposit_amount"])
            commission_amount = round(deposit * rate / 100, 2)
            
            # Robust payment lookup: try reference first, then any payment on this invoice with 'deposit'
            ref = f"{verify_rec['payment_date']}_form_deposit"
            pay_res = db.table("payments").select("id").eq("invoice_id", invoice["id"]).eq("reference", ref).execute()
            if not pay_res.data:
                # Fallback: find any payment on this invoice with webhook-style reference
                pay_res = db.table("payments")\
                    .select("id")\
                    .eq("invoice_id", invoice["id"])\
                    .ilike("reference", "%form_deposit")\
                    .execute()
                    
            payment_id = pay_res.data[0]["id"] if pay_res.data else None
            
            if payment_id:
                # Insert earnings record
                earning = db.table("commission_earnings").insert({
                    "sales_rep_id": rep_id,
                    "invoice_id": invoice["id"],
                    "payment_id": payment_id,
                    "client_id": client["id"],
                    "estate_name": invoice["property_name"],
                    "payment_amount": deposit,
                    "commission_rate": rate,
                    "commission_amount": commission_amount,
                }).execute().data[0]
                
                if rep:
                    background_tasks.add_task(
                        send_commission_earned_email,
                        rep=rep,
                        client=client,
                        invoice=invoice,
                        earning=earning
                    )

    # 4. Send Documents
    background_tasks.add_task(send_receipt_and_statement_email, invoice, client, all_inv.data)

    # 5. Log emails
    for doc_type in ["receipt", "statement"]:
        log_data = jsonable_encoder({
            "client_id": client["id"],
            "invoice_id": invoice["id"],
            "email_type": doc_type,
            "recipient_email": client["email"],
            "subject": f"Payment Confirmed — {invoice['invoice_number']}",
            "status": "sent",
            "sent_by": current_admin["sub"]
        })
        db.table("email_logs").insert(log_data).execute()

    background_tasks.add_task(
        log_activity,
        "payment_confirmed",
        f"Payment confirmed for {invoice['invoice_number']}",
        current_admin["sub"],
        client_id=client["id"],
        invoice_id=invoice["id"]
    )

    return {"message": "Payment confirmed and documents sent"}

@router.patch("/{id}/reject")
async def reject_verification(
    id: str, 
    data: VerificationReject,
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    db = get_db()
    
    # 1. Fetch verification record
    v_res = db.table("pending_verifications").select("*").eq("id", id).execute()
    if not v_res.data:
        raise HTTPException(status_code=404, detail="Verification record not found")
    
    verify_rec = v_res.data[0]
    
    # 2. Update verification status
    db.table("pending_verifications").update({
        "status": "rejected",
        "rejection_reason": data.reason,
        "reviewed_by": current_admin["sub"],
        "reviewed_at": datetime.now().isoformat()
    }).eq("id", id).execute()

    # 3. Mark invoice form deposit payments as voided so they are excluded from
    # revenue analytics, statements, and commission calculations.
    payment_query = db.table("payments")
    payment_query = payment_query.select("*")
    payment_query = payment_query.eq("invoice_id", verify_rec["invoice_id"])
    payment_query = payment_query.eq("is_voided", False)
    payment_query = payment_query.ilike("reference", "%form_deposit")
    payments_to_void = payment_query.execute().data or []

    if not payments_to_void and verify_rec.get("deposit_amount") is not None:
        # Fallback: match deposit amount and form deposit note if the reference
        # changed or was missing.
        payments_to_void = db.table("payments")\
            .select("*")\
            .eq("invoice_id", verify_rec["invoice_id"])\
            .eq("is_voided", False)\
            .eq("amount", verify_rec["deposit_amount"])\
            .ilike("notes", "%subscription form%")\
            .execute().data or []

    if payments_to_void:
        payment_ids = [p["id"] for p in payments_to_void]
        db.table("payments").update({
            "is_voided": True,
            "voided_by": current_admin["sub"],
            "voided_at": datetime.now().isoformat(),
            "notes": f"Rejected during verification: {data.reason}"
        }).in_("id", payment_ids).execute()

        db.table("commission_earnings").update({
            "is_voided": True,
            "voided_by": current_admin["sub"],
            "voided_at": datetime.now().isoformat(),
            "void_reason": f"Rejected during verification: {data.reason}"
        }).in_("payment_id", payment_ids).execute()
    
    # 4. Fetch invoice and client for email
    inv_res = db.table("invoices").select("*, clients(*)").eq("id", verify_rec["invoice_id"]).execute()
    invoice = inv_res.data[0]
    client = invoice["clients"]

    # 5. Send Rejection Email
    background_tasks.add_task(send_rejection_email, invoice, client, data.reason)

    background_tasks.add_task(
        log_activity,
        "submission_rejected",
        f"Form submission for {invoice['invoice_number']} rejected: {data.reason}",
        current_admin["sub"],
        client_id=client["id"],
        invoice_id=invoice["id"]
    )

    return {"message": "Submission rejected and client notified"}

@router.patch("/{id}/edit")
async def edit_verification(
    id: str,
    payload: VerificationUpdate,
    current_admin=Depends(verify_token)
):
    db = get_db()
    role = current_admin.get("role")
    
    # 1. Fetch verification
    v_res = db.table("pending_verifications").select("*").eq("id", id).execute()
    if not v_res.data:
        raise HTTPException(status_code=404, detail="Verification record not found")
    
    verify_rec = v_res.data[0]
    
    update_data = jsonable_encoder(payload, exclude_none=True)
    if not update_data:
        return {"message": "No changes applied"}

    # Field-level role checks
    admin_only_fields = ["deposit_amount", "payment_date"]
    
    if role != "admin":
        for field in admin_only_fields:
            if field in update_data:
                raise HTTPException(status_code=403, detail=f"Permission denied to edit {field}")

    # 2. Update verification
    db.table("pending_verifications").update(update_data).eq("id", id).execute()
    
    # If deposit amount changed, update the linked payment record if it exists
    if "deposit_amount" in update_data:
        ref = f"{verify_rec['payment_date']}_form_deposit"
        db.table("payments").update({"amount": update_data["deposit_amount"]})\
            .eq("invoice_id", verify_rec["invoice_id"])\
            .eq("reference", ref)\
            .execute()

    return {"message": "Verification updated successfully"}

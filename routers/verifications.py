from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from models import VerificationConfirm, VerificationReject, VerificationUpdate
from database import get_db
from routers.auth import verify_token
from email_service import send_receipt_and_statement_email, send_rejection_email, send_commission_earned_email
from routers.analytics import log_activity
from datetime import datetime, date

def get_commission_rate(sales_rep_id: str, estate_name: str, verification_date: date, db) -> float:
    result = db.table("commission_rates")\
        .select("rate")\
        .eq("sales_rep_id", sales_rep_id)\
        .eq("estate_name", estate_name)\
        .lte("effective_from", str(verification_date))\
        .or_(f"effective_to.is.null,effective_to.gte.{verification_date}")\
        .order("effective_from", desc=True)\
        .limit(1)\
        .execute()
    if result.data:
        return float(result.data[0]["rate"])

    default = db.table("system_settings")\
        .select("value")\
        .eq("key", "default_commission_rate")\
        .execute()
    return float(default.data[0]["value"]) if default.data else 5.0

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

    if invoice.get("sales_rep_name"):
        rep_res = db.table("sales_reps").select("*").eq("name", invoice["sales_rep_name"]).execute()
        if rep_res.data:
            rep = rep_res.data[0]
            rep_id = rep["id"]
            rate = get_commission_rate(
                sales_rep_id=rep_id,
                estate_name=invoice["property_name"],
                verification_date=date.today(),
                db=db
            )
            deposit = float(verify_rec["deposit_amount"])
            commission_amount = round(deposit * rate / 100, 2)
            
            ref = f"{verify_rec['payment_date']}_form_deposit"
            pay_res = db.table("payments").select("id").eq("invoice_id", invoice["id"]).eq("reference", ref).execute()
            payment_id = pay_res.data[0]["id"] if pay_res.data else None
            
            if payment_id:
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

    # 3. Mark invoice as unpaid (reverse local amount_paid tracking if any? 
    # Actually the trigger handles it via payments. 
    # But if there was a payment record created during webhook, it stays there. 
    # The PRD says "Marks the invoice status back to unpaid".
    
    # Let's find the payment record tied to this form deposit and mark it as voided?
    # PRD Section 4.5 doesn't explicitly say to delete the payment record, 
    # but 5.3 mentions is_voided for manual voiding.
    # I'll mark the payment as voided to be consistent.
    
    ref = f"{verify_rec['payment_date']}_form_deposit"
    db.table("payments").update({
        "is_voided": True,
        "voided_by": current_admin["sub"],
        "voided_at": datetime.now().isoformat(),
        "notes": f"Rejected during verification: {data.reason}"
    }).eq("invoice_id", verify_rec["invoice_id"]).eq("reference", ref).execute()

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

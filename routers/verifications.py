from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from models import VerificationConfirm, VerificationReject, VerificationUpdate
from database import get_db, db_execute
from routers.auth import verify_token, has_any_role
from email_service import send_receipt_and_statement_email, send_rejection_email, send_commission_earned_email
from routers.analytics import log_activity
from datetime import datetime, date

from commission_service import get_commission_config
# Re-exported for other modules that depend on it

router = APIRouter()

@router.get("/")
async def list_verifications(current_admin=Depends(verify_token)):
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])

    # Fetch pending verifications with client, invoice, and subscription info
    # Use !inner to ensure that the row is completely excluded if the client filter doesn't match
    query = db.table("pending_verifications")\
        .select("*, clients!inner(full_name, email, assigned_rep_id), invoices(invoice_number, property_name, plot_size_sqm, amount, amount_paid, signature_url), property_subscriptions(passport_photo_url, nin_document_url, international_passport_url, occupation, residential_address)")\
        .order("created_at", desc=True)
    
    if not is_privileged:
        # Join check: filter where the client's assigned rep is the current user
        query = query.filter("clients.assigned_rep_id", "eq", admin_id)

    result = await db_execute(lambda: query.execute())
    return result.data

@router.get("/count")
async def get_pending_count(current_admin=Depends(verify_token)):
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])

    query = db.table("pending_verifications")\
        .select("id, clients!inner(assigned_rep_id)", count="exact")\
        .eq("status", "pending")
    
    if not is_privileged:
        query = query.filter("clients.assigned_rep_id", "eq", admin_id)

    result = await db_execute(lambda: query.execute())
    return {"count": result.count or 0}

@router.patch("/{id}/confirm")
async def confirm_verification(
    id: str, 
    background_tasks: BackgroundTasks,
    payload: Optional[VerificationConfirm] = None,
    current_admin=Depends(verify_token)
):
    db = get_db()
    do_send_email = payload.send_email if payload else True
    
    # 1. Fetch verification record
    if not has_any_role(current_admin, "admin", "super_admin", "operations"):
        raise HTTPException(status_code=403, detail="Unauthorized: Only admins can confirm verifications")

    v_res = await db_execute(lambda: db.table("pending_verifications").select("*").eq("id", id).execute())
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
    await db_execute(lambda: db.table("pending_verifications").update(update_data).eq("id", id).execute())

    # 3. Ensure payment is created in payments table if missing
    deposit = float(verify_rec.get("deposit_amount") or 0)
    payment_id = None
    if deposit > 0:
        pay_res = await db_execute(lambda: db.table("payments")\
            .select("id")\
            .eq("invoice_id", verify_rec["invoice_id"])\
            .eq("is_voided", False)\
            .ilike("reference", f"%{verify_rec['id'][:8]}%")\
            .execute())
        if not pay_res.data:
            pay_res = await db_execute(lambda: db.table("payments")\
                .select("id")\
                .eq("invoice_id", verify_rec["invoice_id"])\
                .eq("is_voided", False)\
                .eq("amount", deposit)\
                .eq("payment_date", verify_rec.get("payment_date"))\
                .execute())

        if pay_res.data:
            payment_id = pay_res.data[0]["id"]
        else:
            ref = f"{verify_rec.get('payment_date') or str(date.today())}_verified_{verify_rec['id'][:8]}"
            pmt_insert = {
                "invoice_id": verify_rec["invoice_id"],
                "client_id": verify_rec["client_id"],
                "reference": ref,
                "amount": deposit,
                "payment_method": "Bank Transfer",
                "payment_date": verify_rec.get("payment_date") or str(date.today()),
                "notes": f"Verified payment submission (Ref {verify_rec['id'][:8]})"
            }
            pmt_res = await db_execute(lambda: db.table("payments").insert(jsonable_encoder(pmt_insert)).execute())
            if pmt_res.data:
                payment_id = pmt_res.data[0]["id"]

    # 4. Fetch invoice with clients AND payments for complete receipt rendering
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*), payments(*)").eq("id", verify_rec["invoice_id"]).execute())
    invoice = inv_res.data[0]
    client = invoice["clients"]

    # Calculate actual totals and update invoice status/amount_paid
    valid_payments = [p for p in (invoice.get("payments") or []) if not p.get("is_voided")]
    total_paid = sum(float(p["amount"]) for p in valid_payments if p.get("payment_type") != "refund")
    invoice_amount = float(invoice.get("amount") or 0)
    new_status = "paid" if total_paid >= invoice_amount else ("partial" if total_paid > 0 else "unpaid")

    await db_execute(lambda: db.table("invoices").update({
        "amount_paid": total_paid,
        "status": new_status,
        "updated_at": datetime.now().isoformat()
    }).eq("id", invoice["id"]).execute())

    invoice["amount_paid"] = total_paid
    invoice["balance_due"] = max(0.0, invoice_amount - total_paid)
    invoice["status"] = new_status

    # Fetch all invoices for statement
    all_inv = await db_execute(lambda: db.table("invoices")\
        .select("*, payments(*)")\
        .eq("client_id", client["id"])\
        .order("invoice_date")\
        .execute())

    rep_id = invoice.get("sales_rep_id")
    rep = None
    if not rep_id and invoice.get("sales_rep_name"):
        rep_name = invoice["sales_rep_name"].strip()
        rep_res = await db_execute(lambda: db.table("sales_reps")\
            .select("*")\
            .ilike("name", f"%{rep_name}%")\
            .eq("is_active", True)\
            .execute())
        if rep_res.data:
            rep = rep_res.data[0]
            rep_id = rep["id"]

    if rep_id and not rep:
        rep_res = await db_execute(lambda: db.table("sales_reps").select("*").eq("id", rep_id).execute())
        if rep_res.data:
            rep = rep_res.data[0]
            
    if rep_id and payment_id:
        config = get_commission_config(
            sales_rep_id=rep_id,
            estate_name=invoice.get("property_name", ""),
            verification_date=date.today(),
            db=db
        )
        gross_comm = round(deposit * config["gross_rate"] / 100, 2)
        wht_amt = round(gross_comm * config["wht_rate"] / 100, 2)
        net_comm = gross_comm - wht_amt
        
        earning_res = await db_execute(lambda: db.table("commission_earnings").insert({
            "sales_rep_id": rep_id,
            "invoice_id": invoice["id"],
            "payment_id": payment_id,
            "client_id": client["id"],
            "estate_name": invoice.get("property_name", ""),
            "payment_amount": deposit,
            "commission_rate": config["gross_rate"],
            "commission_amount": net_comm,
            "gross_commission": gross_comm,
            "wht_amount": wht_amt,
            "net_commission": net_comm
        }).execute())
        
        if earning_res.data and rep:
            background_tasks.add_task(
                send_commission_earned_email,
                rep=rep,
                client=client,
                invoice=invoice,
                earning=earning_res.data[0]
            )

    # 5. Send Documents & Log Emails (Only if send_email is True)
    if do_send_email:
        background_tasks.add_task(send_receipt_and_statement_email, invoice, client, all_inv.data)
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
            await db_execute(lambda: db.table("email_logs").insert(log_data).execute())

    background_tasks.add_task(
        log_activity,
        "payment_confirmed",
        f"Payment confirmed for {invoice['invoice_number']}",
        current_admin["sub"],
        client_id=client["id"],
        invoice_id=invoice["id"]
    )

    return {"message": "Payment confirmed successfully"}

@router.patch("/{id}/reject")
async def reject_verification(
    id: str, 
    data: VerificationReject,
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    db = get_db()
    
    # 1. Fetch verification record
    if not has_any_role(current_admin, "admin", "super_admin", "operations"):
        raise HTTPException(status_code=403, detail="Unauthorized: Only admins can reject verifications")

    v_res = await db_execute(lambda: db.table("pending_verifications").select("*").eq("id", id).execute())
    if not v_res.data:
        raise HTTPException(status_code=404, detail="Verification record not found")
    
    verify_rec = v_res.data[0]
    
    # 2. Update verification status
    await db_execute(lambda: db.table("pending_verifications").update({
        "status": "rejected",
        "rejection_reason": data.reason,
        "reviewed_by": current_admin["sub"],
        "reviewed_at": datetime.now().isoformat()
    }).eq("id", id).execute())

    # 3. Mark invoice form deposit payments as voided so they are excluded from
    # revenue analytics, statements, and commission calculations.
    payment_query = db.table("payments")
    payment_query = payment_query.select("*")
    payment_query = payment_query.eq("invoice_id", verify_rec["invoice_id"])
    payment_query = payment_query.eq("is_voided", False)
    payment_query = payment_query.ilike("reference", "%form_deposit")
    pmt_res = await db_execute(lambda: payment_query.execute())
    payments_to_void = pmt_res.data or []

    if not payments_to_void and verify_rec.get("deposit_amount") is not None:
        # Fallback: match deposit amount and form deposit note if the reference
        # changed or was missing.
        pmt_res = await db_execute(lambda: db.table("payments")\
            .select("*")\
            .eq("invoice_id", verify_rec["invoice_id"])\
            .eq("is_voided", False)\
            .eq("amount", verify_rec["deposit_amount"])\
            .ilike("notes", "%subscription form%")\
            .execute())
        payments_to_void = pmt_res.data or []

    if payments_to_void:
        payment_ids = [p["id"] for p in payments_to_void]
        await db_execute(lambda: db.table("payments").update({
            "is_voided": True,
            "voided_by": current_admin["sub"],
            "voided_at": datetime.now().isoformat(),
            "notes": f"Rejected during verification: {data.reason}"
        }).in_("id", payment_ids).execute())

        await db_execute(lambda: db.table("commission_earnings").update({
            "is_voided": True,
            "voided_by": current_admin["sub"],
            "voided_at": datetime.now().isoformat(),
            "void_reason": f"Rejected during verification: {data.reason}"
        }).in_("payment_id", payment_ids).execute())
    
    # 4. Fetch invoice and client for email
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", verify_rec["invoice_id"]).execute())
    invoice = inv_res.data[0]
    client = invoice["clients"]

    # 5. Send Rejection Email (Only if send_email is True)
    if data.send_email:
        background_tasks.add_task(send_rejection_email, invoice, client, data.reason)

    # 6. Final Sync of Commissions (Catch-all)
    from commission_service import sync_invoice_commissions
    background_tasks.add_task(
        sync_invoice_commissions,
        invoice_id=verify_rec["invoice_id"],
        db=db,
        performed_by=current_admin["sub"]
    )

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
    v_res = await db_execute(lambda: db.table("pending_verifications").select("*").eq("id", id).execute())
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
    await db_execute(lambda: db.table("pending_verifications").update(update_data).eq("id", id).execute())
    
    # If deposit amount changed, update the linked payment record if it exists
    if "deposit_amount" in update_data:
        ref = f"{verify_rec['payment_date']}_form_deposit"
        db.table("payments").update({"amount": update_data["deposit_amount"]})\
            .eq("invoice_id", verify_rec["invoice_id"])\
            .eq("reference", ref)\
            .execute()

    return {"message": "Verification updated successfully"}

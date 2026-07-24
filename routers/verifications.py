from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder
from models import VerificationConfirm, VerificationReject, VerificationUpdate
from database import get_db, db_execute
from routers.auth import verify_token, resolve_admin_token, has_any_role
from email_service import send_receipt_and_statement_email, send_rejection_email, send_commission_earned_email
from routers.analytics import log_activity
from datetime import datetime, date

from commission_service import get_commission_config
# Re-exported for other modules that depend on it

router = APIRouter()


@router.get("/{id}/view-proof")
async def view_verification_proof(id: str, current_admin=Depends(resolve_admin_token)):
    """
    Return a short-lived signed URL for the payment_proof_url attached to a
    pending_verifications row.  The stored value is a private bucket path
    (not a public URL), so we must generate a signed URL before the browser
    can display it.
    """
    from storage_service import generate_signed_url

    db = get_db()
    res = await db_execute(
        lambda: db.table("pending_verifications")
        .select("payment_proof_url")
        .eq("id", id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Verification record not found")

    path = res.data[0].get("payment_proof_url")
    if not path:
        raise HTTPException(status_code=404, detail="No proof file attached to this record")

    import json
    from fastapi.responses import HTMLResponse

    paths = []
    if isinstance(path, list):
        paths = path
    elif isinstance(path, str):
        if path.startswith("["):
            try:
                paths = json.loads(path)
            except:
                paths = [path]
        else:
            paths = [path]
    else:
        paths = [str(path)]

    urls = []
    for p in paths:
        if p.startswith("http"):
            urls.append({"url": p, "path": p, "success": True})
        else:
            s_url = generate_signed_url("Cloud Infrastructure", p)
            if s_url:
                urls.append({"url": s_url, "path": p, "success": True})
            else:
                urls.append({"url": "", "path": p, "success": False})

    # If only one file and it succeeded, redirect directly
    if len(urls) == 1 and urls[0]["success"]:
        return RedirectResponse(url=urls[0]["url"])

    html_content = "<html><body style='font-family:sans-serif; padding: 20px; text-align: center; background: #f9f9f9;'>"
    html_content += "<h2 style='color: #333;'>Payment Receipts</h2>"
    
    for i, item in enumerate(urls):
        if item["success"]:
            html_content += f"<div style='margin-bottom: 10px;'><a href='{item['url']}' target='_blank' style='display:inline-block; padding:10px 20px; background:#1a5fb4; color:white; text-decoration:none; border-radius:5px; font-weight: bold;'>Open Receipt {i+1} in New Tab</a></div>"
            html_content += f"<div style='margin-bottom: 40px;'><iframe src='{item['url']}' style='width:90%; max-width: 800px; height:600px; border:1px solid #ccc; background: white; border-radius: 8px;'></iframe></div>"
        else:
            html_content += f"<div style='margin-bottom: 40px; padding: 20px; border: 1px solid #f5c6cb; background: #f8d7da; color: #721c24; border-radius: 8px; width: 90%; max-width: 800px; margin-left: auto; margin-right: auto;'>"
            html_content += f"<h3>Failed to load receipt {i+1}</h3>"
            html_content += f"<p>Could not generate a secure link for: <strong>{item['path']}</strong></p>"
            html_content += f"<p>This usually means the file does not exist in the Storage bucket at this exact path.</p>"
            html_content += f"</div>"
            
    html_content += "</body></html>"
    
    return HTMLResponse(content=html_content)

@router.get("/")
async def list_verifications(current_admin=Depends(verify_token)):
    db = get_db()
    role = current_admin.get("role", "")
    admin_id = current_admin["sub"]
    is_privileged = any(r in role.lower() for r in ["admin", "operations"])

    # Fetch pending verifications with client, invoice, and subscription info
    # Use !inner to ensure that the row is completely excluded if the client filter doesn't match
    query = db.table("pending_verifications")\
        .select("*, clients!inner(full_name, email, assigned_rep_id), invoices(invoice_number, property_name, plot_size_sqm, amount, amount_paid, signature_url, discount_code, discount_amount), property_subscriptions(passport_photo_url, nin_document_url, international_passport_url, occupation, residential_address)")\
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

    # 3. Fetch invoice with clients AND payments for complete receipt rendering
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*), payments(*)").eq("id", verify_rec["invoice_id"]).execute())
    invoice = inv_res.data[0]
    client = invoice["clients"]

    # Upgrade placeholder client email if needed
    client_email = client.get("email") or ""
    is_placeholder = client_email.startswith("lead_") or client_email.endswith("@temp-eximps.com")
    if is_placeholder and verify_rec.get("subscription_id"):
        try:
            sub_res = await db_execute(
                lambda: db.table("property_subscriptions")
                .select("email")
                .eq("id", verify_rec["subscription_id"])
                .execute()
            )
            sub_email = (sub_res.data[0].get("email") or "").strip().lower() if sub_res.data else ""
            if sub_email and not sub_email.startswith("lead_") and "@" in sub_email:
                await db_execute(
                    lambda: db.table("clients")
                    .update({"email": sub_email})
                    .eq("id", client["id"])
                    .execute()
                )
                client["email"] = sub_email
        except Exception as email_fix_err:
            print(f"[WARN] Could not upgrade placeholder email at verification: {email_fix_err}")

    # 3a. Sync pipeline_stage on invoice + client now that payment is confirmed.
    # Mirrors the same logic in routers/payments.py (lines 124-127).
    # Wrapped in try/except so it never prevents the confirmation from completing.
    try:
        total_due  = float(invoice.get("amount") or 0)
        total_paid = float(invoice.get("amount_paid") or 0)

        if total_due > 0 and total_paid >= total_due:
            # Fully paid — no balance remaining
            new_inv_stage    = "paid"
            new_client_stage = "closed"
            new_inv_status   = "paid"
        elif total_paid > 0:
            # Has paid something but still owes a balance
            new_inv_stage    = "interest"
            new_client_stage = "paid"
            new_inv_status   = "partial"
        else:
            # No payment recorded yet (edge case — shouldn't happen on confirm)
            new_inv_stage    = "interest"
            new_client_stage = "interest"
            new_inv_status   = "unpaid"

        await db_execute(lambda: db.table("invoices").update({
            "pipeline_stage": new_inv_stage,
            "status": new_inv_status,
        }).eq("id", verify_rec["invoice_id"]).execute())

        await db_execute(lambda: db.table("clients").update({
            "pipeline_stage": new_client_stage,
        }).eq("id", client["id"]).execute())

    except Exception as stage_err:
        print(f"[WARN] Pipeline stage sync after verification failed (non-critical): {stage_err}")
>>>>>>> a91ab755069829a8fb327a5e1c7cd55680947ff6

    # Fetch all invoices for statement
    all_inv = await db_execute(lambda: db.table("invoices")\
        .select("*, payments(*)")\
        .eq("client_id", client["id"])\
        .neq("status", "voided")\
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
            
    payment_id = None
    if deposit > 0:
        is_portal_source = verify_rec.get("source") == "portal"

        if is_portal_source:
            _sys_res = await db_execute(lambda: db.table("system_settings")
                .select("key, value")
                .in_("key", ["default_commission_rate", "default_partner_commission_rate", "default_wht_rate"])
                .execute()
            )
            _sys = {s["key"]: s["value"] for s in (_sys_res.data or [])}

            def _pct(key, fallback):
                try:
                    v = float(_sys.get(key) or fallback)
                    return v if v <= 1 else v / 100
                except Exception:
                    return fallback

            sub_type = verify_rec.get("submission_type", "")
            if sub_type == "partner":
                gross_rate = _pct("default_partner_commission_rate", 0.15)
            else:
                gross_rate = _pct("default_commission_rate", 0.10)
            wht_rate = _pct("default_wht_rate", 0.05)

            has_itemization = invoice.get("land_cost") is not None
            if has_itemization:
                amount = float(invoice.get("amount") or 1.0)
                land_cost = float(invoice.get("land_cost") or 0.0)
                ratio = land_cost / amount if amount > 0 else 0.90
                commission_base = deposit * ratio
            else:
                commission_base = deposit
            gross_comm = round(commission_base * gross_rate, 2)
            wht_amt    = round(gross_comm * wht_rate, 2)
            net_comm   = gross_comm - wht_amt
        else:
            if rep_id:
                config = get_commission_config(
                    sales_rep_id=rep_id,
                    estate_name=invoice.get("property_name", ""),
                    verification_date=date.today(),
                    db=db
                )
            else:
                config = {"gross_rate": 10.0, "wht_rate": 5.0}

            has_itemization = invoice.get("land_cost") is not None
            if has_itemization:
                amount = float(invoice.get("amount") or 1.0)
                land_cost = float(invoice.get("land_cost") or 0.0)
                ratio = land_cost / amount if amount > 0 else 0.90
                commission_base = deposit * ratio
            else:
                commission_base = deposit
            gross_comm = round(commission_base * config["gross_rate"] / 100, 2)
            wht_amt    = round(gross_comm * config["wht_rate"] / 100, 2)
            net_comm   = gross_comm - wht_amt

        if is_portal_source:
            ref = f"{verify_rec['payment_date']}_portal_reported"
        else:
            ref = f"{verify_rec.get('payment_date') or str(date.today())}_verified_{verify_rec['id'][:8]}"

        # Void superseded placeholder payments for this invoice
        placeholder_res = await db_execute(lambda: db.table("payments")
            .select("id, reference, payment_method")
            .eq("invoice_id", invoice["id"])
            .eq("is_voided", False)
            .execute())

        if placeholder_res.data:
            placeholder_ids = [
                p["id"] for p in placeholder_res.data
                if (
                    "_portal_reported" in str(p.get("reference", "")) or
                    "_form_deposit" in str(p.get("reference", "")) or
                    str(p.get("reference", "")).startswith("CLAIM-") or
                    p.get("payment_method") == "portal_reported"
                )
            ]
            if placeholder_ids:
                await db_execute(lambda: db.table("payments").update({
                    "is_voided": True,
                    "notes": "Auto-voided at verification: superseded by Finance-confirmed payment"
                }).in_("id", placeholder_ids).execute())

        payment_payload = {
            "invoice_id": invoice["id"],
            "client_id": client["id"],
            "amount": deposit,
            "reference": ref,
            "payment_date": verify_rec.get("payment_date") or str(date.today()),
            "payment_method": "Bank Transfer",
            "notes": "Verified portal-reported payment" if is_portal_source else f"Verified payment submission (Ref {verify_rec['id'][:8]})"
        }
        new_pay = await db_execute(lambda: db.table("payments").insert(jsonable_encoder(payment_payload)).execute())
        if new_pay.data:
            payment_id = new_pay.data[0]["id"]
        
        if payment_id and (rep_id or verify_rec.get("submission_type") == "partner"):
            stored_rate = round(gross_rate * 100, 4) if is_portal_source else config["gross_rate"]
            is_partner = (verify_rec.get("submission_type") == "partner")
            
            earning_payload = {
                "invoice_id": invoice["id"],
                "payment_id": payment_id,
                "client_id": client["id"],
                "estate_name": invoice.get("property_name", ""),
                "payment_amount": deposit,
                "commission_rate": stored_rate,
                "commission_amount": net_comm, 
                "gross_commission": gross_comm,
                "wht_amount": wht_amt,
                "net_commission": net_comm
            }
            
            if is_partner:
                email_to_use = verify_rec.get("sales_rep_email") or verify_rec.get("sales_rep_name")
                v_res = await db_execute(lambda: db.table("vendors").select("id").eq("email", email_to_use).execute())
                if v_res.data:
                    earning_payload["vendor_id"] = v_res.data[0]["id"]
                else:
                    try:
                        exp_res = await db_execute(lambda: db.table("expenditure_requests").select("vendor_id").eq("pending_verification_id", id).execute())
                        if exp_res.data and exp_res.data[0].get("vendor_id"):
                            earning_payload["vendor_id"] = exp_res.data[0]["vendor_id"]
                    except Exception:
                        pass
            else:
                earning_payload["sales_rep_id"] = rep_id

            earning_res = await db_execute(lambda: db.table("commission_earnings").insert(earning_payload).execute())
            
            if is_portal_source:
                await db_execute(lambda: db.table("expenditure_requests")
                    .update({
                        "status": "approved",
                        "payment_id": payment_id,
                        "hr_note": f"Auto-approved via Verification #{id}"
                    })
                    .eq("pending_verification_id", id)
                    .execute()
                )
            
            if earning_res.data and rep:
                background_tasks.add_task(
                    send_commission_earned_email,
                    rep=rep,
                    client=client,
                    invoice=invoice,
                    earning=earning_res.data[0]
                )
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
    # BUG FIX #6: Also match portal_reported payments (not just form_deposit)
    # Portal submissions use reference pattern like "CLAIM-xxx" or payment_method "portal_reported"
    payment_query = db.table("payments")
    payment_query = payment_query.select("*")
    payment_query = payment_query.eq("invoice_id", verify_rec["invoice_id"])
    payment_query = payment_query.eq("is_voided", False)
    
    # Query for form_deposit payments
    pmt_res = await db_execute(lambda: payment_query.ilike("reference", "%form_deposit").execute())
    payments_to_void = pmt_res.data or []
    
    # Also query for portal_reported payments (CLAIM-* reference or payment_method = portal_reported)
    portal_query = db.table("payments")
    portal_query = portal_query.select("*")
    portal_query = portal_query.eq("invoice_id", verify_rec["invoice_id"])
    portal_query = portal_query.eq("is_voided", False)
    portal_query = portal_query.eq("payment_method", "portal_reported")
    portal_res = await db_execute(lambda: portal_query.execute())
    
    # Combine both lists, avoiding duplicates
    portal_payments = portal_res.data or []
    all_payment_ids = [p["id"] for p in payments_to_void] + [p["id"] for p in portal_payments if p["id"] not in [pv["id"] for pv in payments_to_void]]
    
    # Update payments_to_void to include both types
    payments_to_void = payments_to_void + [p for p in portal_payments if p["id"] not in [pv["id"] for pv in payments_to_void]]

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
    
    if not has_any_role(current_admin, "admin"):
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
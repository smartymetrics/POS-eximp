from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from models import InvoiceCreate, SendDocumentRequest, VoidReceiptRequest
from database import get_db
from routers.auth import verify_token, resolve_admin_token
from routers.analytics import log_activity
from email_service import send_invoice_email, send_receipt_email, send_statement_email, send_void_notification_email
from pdf_service import generate_invoice_pdf, generate_receipt_pdf, generate_statement_pdf
from utils import resolve_invoice_status
from commission_service import sync_invoice_commissions
from datetime import datetime
import io

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def list_invoices(show_voided: bool = False, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("invoices").select("*, clients(full_name, email)")
    
    if not show_voided:
        query = query.neq("status", "voided")
        
    result = query.order("created_at", desc=True).execute()
    
    invoices = result.data
    for inv in invoices:
        inv["status"] = resolve_invoice_status(inv)
    
    return invoices


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("invoices")\
        .select("*, clients(*), payments(*), email_logs(*, admins!sent_by(full_name))")\
        .eq("id", invoice_id)\
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = result.data[0]
    invoice["status"] = resolve_invoice_status(invoice)
    
    # Fallback for missing location data
    if not invoice.get("property_location") and invoice.get("property_name"):
        prop_res = db.table("properties").select("location").ilike("name", f"%{invoice['property_name']}%").execute()
        if prop_res.data:
            invoice["property_location"] = prop_res.data[0]["location"]
            
    return invoice


@router.post("/")
async def create_invoice(
    data: InvoiceCreate, 
    background_tasks: BackgroundTasks, 
    current_admin=Depends(verify_token)
):
    db = get_db()

    # Generate invoice number via DB function
    seq_result = db.rpc("generate_invoice_number").execute()
    invoice_number = seq_result.data

    # If property_id provided, snapshot the property details
    property_name = data.property_name
    property_location = data.property_location
    plot_size = data.plot_size_sqm

    if data.property_id:
        prop = db.table("properties").select("*").eq("id", data.property_id).execute()
        if prop.data:
            p = prop.data[0]
            property_name = property_name or p["name"]
            property_location = property_location or p["location"]
            plot_size = plot_size or p["plot_size_sqm"]

    invoice_data = {
        "invoice_number": invoice_number,
        "client_id": data.client_id,
        "property_id": data.property_id,
        "property_name": property_name,
        "property_location": property_location,
        "plot_size_sqm": plot_size,
        "quantity": data.quantity,
        "unit_price": data.unit_price,
        "amount": data.amount,
        "payment_terms": data.payment_terms,
        "invoice_date": data.invoice_date,
        "due_date": data.due_date,
        "notes": data.notes,
        "created_by": current_admin["sub"]
    }
    
    # Use jsonable_encoder to handle Decimal/date types for Supabase
    encoded_data = jsonable_encoder(invoice_data)
    result = db.table("invoices").insert(encoded_data).execute()

    background_tasks.add_task(
        log_activity,
        "invoice_created",
        f"Invoice {invoice_number} created for {data.client_id}",
        current_admin["sub"],
        client_id=data.client_id,
        invoice_id=result.data[0]["id"]
    )

    return {"message": "Invoice created", "invoice": result.data[0]}


@router.post("/send")
async def send_documents(
    data: SendDocumentRequest,
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    db = get_db()

    # Fetch full invoice data
    inv = db.table("invoices")\
        .select("*, clients(*), payments(*)")\
        .eq("id", data.invoice_id)\
        .execute()

    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = inv.data[0]
    client_raw = invoice.get("clients", {})
    # Handle both list and dict returns from Supabase-js style mapping
    client = client_raw[0] if isinstance(client_raw, list) and client_raw else client_raw
    if not client: client = {}

    sent = []

    try:
        for doc_type in data.document_types:
            if doc_type == "invoice":
                await send_invoice_email(invoice, client, current_admin["sub"])
                sent.append("invoice")
                background_tasks.add_task(
                    log_activity,
                    "receipt_sent",
                    f"Invoice {invoice['invoice_number']} sent to {client['email']}",
                    current_admin["sub"],
                    client_id=client["id"],
                    invoice_id=invoice["id"]
                )
            elif doc_type == "receipt" and invoice["amount_paid"] > 0:
                await send_receipt_email(invoice, client, current_admin["sub"])
                sent.append("receipt")
            elif doc_type == "refund_receipt":
                # Find the most recent refund to send
                refunds = [p for p in invoice.get("payments", []) if p.get("payment_type") == "refund"]
                if refunds:
                    latest_refund = sorted(refunds, key=lambda x: x["created_at"], reverse=True)[0]
                    from email_service import send_refund_receipt_email
                    await send_refund_receipt_email(invoice, latest_refund, client)
                    sent.append("refund_receipt")
            elif doc_type == "statement":
                # Fetch all invoices for this client
                all_inv = db.table("invoices")\
                    .select("*, payments(*)")\
                    .eq("client_id", invoice["client_id"])\
                    .neq("status", "voided")\
                    .order("invoice_date")\
                    .execute()
                await send_statement_email(all_inv.data, client, current_admin["sub"])
                sent.append("statement")
            elif doc_type == "contract":
                # To send a contract, we check if there's an active or completed session
                session_res = db.table("contract_signing_sessions")\
                    .select("*, witness_signatures(*)")\
                    .eq("invoice_id", invoice["id"])\
                    .order("created_at", desc=True)\
                    .limit(1)\
                    .execute()
                
                if session_res.data:
                    session = session_res.data[0]
                    if session["status"] == "completed":
                        # Send the final executed contract
                        from pdf_service import generate_contract_pdf
                        from email_service import send_executed_contract_email
                        pdf_content = generate_contract_pdf(invoice, client, session.get("witness_signatures", []), is_draft=False)
                        background_tasks.add_task(send_executed_contract_email, invoice, client, pdf_content)
                        sent.append("contract")
                    else:
                        # Resend the signing link
                        from email_service import send_signing_link_email
                        from datetime import datetime
                        expires_at = datetime.fromisoformat(session["expires_at"].replace('Z', '+00:00'))
                        background_tasks.add_task(send_signing_link_email, invoice, client, session["token"], expires_at)
                        sent.append("contract")
                else:
                    # No session exists? We should probably initiate one if the user checked this
                    # But for now, let's keep it safe. If no session, we can't send.
                    # Or we call initiate_contract_signing? (Requires lawyer/admin role)
                    pass 
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Email Provider Error: {str(e)}")

    # Log emails
    if sent:
        background_tasks.add_task(log_email_sends, db, invoice, client, sent, current_admin["sub"])

    return {"message": f"Sent: {', '.join(sent)}", "sent": sent}


def log_email_sends(db, invoice, client, sent_types, admin_id):
    """Background task to record sent emails in the audit log."""
    try:
        logs = []
        for doc_type in sent_types:
            logs.append({
                "client_id": invoice["client_id"],
                "invoice_id": invoice["id"],
                "email_type": doc_type,
                "recipient_email": client.get("email"),
                "subject": f"Eximp & Cloves - {doc_type.title()} {invoice['invoice_number']}",
                "status": "sent",
                "sent_by": admin_id
            })
        if logs:
            db.table("email_logs").insert(logs).execute()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error logging email sends: {e}")


@router.post("/{invoice_id}/void")
async def void_invoice_receipts(
    invoice_id: str,
    payload: VoidReceiptRequest,
    background_tasks: BackgroundTasks,
    current_admin: dict = Depends(verify_token)
):
    """
    Voids all receipts for an invoice and reverses payments.
    Only Admins can perform this.
    """
    db = get_db()
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can void receipts")
    
    # 1. Fetch invoice to get client_id and check existence
    inv = db.table("invoices").select("*, clients(*)").eq("id", invoice_id).single().execute()
    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice_data = inv.data
    client_name = invoice_data.get("clients", {}).get("full_name", "Client")
    client_email = invoice_data.get("clients", {}).get("email")
    
    # 2. Update all payments for this invoice to is_voided = True
    # In a real scenario, we might want to void specific payments, 
    # but the PRD says "Void Receipt" which usually refers to the collective status.
    # We'll void all non-voided payments for this invoice.
    db.table("payments").update({
        "is_voided": True,
        "voided_at": datetime.utcnow().isoformat(),
        "voided_by": current_admin["sub"]
    }).eq("invoice_id", invoice_id).eq("is_voided", False).execute()

    # 2.2 Void any associated unpaid commission earnings
    db.table("commission_earnings").update({
        "is_voided": True,
        "voided_at": datetime.utcnow().isoformat(),
        "voided_by": current_admin["sub"],
        "void_reason": f"Invoice {invoice_data.get('invoice_number', 'N/A')} voided"
    }).eq("invoice_id", invoice_id).eq("is_paid", False).execute()

    # 2.5 Mark invoice itself as voided
    db.table("invoices").update({"status": "voided"}).eq("id", invoice_id).execute()
    
    # 3. Log the void action
    db.table("void_log").insert({
        "invoice_id": invoice_id,
        "client_id": invoice_data["client_id"],
        "voided_by": current_admin["sub"],
        "reason": payload.reason,
        "notify_client": payload.notify_client
    }).execute()
    
    # 4. Notify client if requested
    if payload.notify_client and client_email:
        await send_void_notification_email(
            invoice_data,
            invoice_data.get("clients", {}),
            payload.reason
        )

    # 5. Commission Sync (Final Cleanup)
    from commission_service import sync_invoice_commissions
    background_tasks.add_task(
        sync_invoice_commissions,
        invoice_id=invoice_id,
        db=db,
        performed_by=current_admin["sub"]
    )
        
    background_tasks.add_task(
        log_activity,
        "receipt_voided",
        f"Receipt for {invoice_data['invoice_number']} voided by Admin",
        current_admin["sub"],
        client_id=invoice_data["client_id"],
        invoice_id=invoice_id
    )

    return {"message": "Invoice receipts voided successfully", "client_notified": payload.notify_client}


@router.patch("/{invoice_id}/edit")
async def edit_invoice(
    invoice_id: str,
    payload: dict, # Using dict to handle field-level role checks easily
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    db = get_db()
    role = current_admin.get("role")
    
    # Fetch existing invoice
    inv_res = db.table("invoices").select("*").eq("id", invoice_id).execute()
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = inv_res.data[0]
    
    # Special handling for paid/voided:
    # We allow editing even if paid (to adjust amounts/plans),
    # but still block voided invoices from being resurrected via edit.
    if invoice.get("status") == "voided":
         raise HTTPException(status_code=400, detail="Voided invoices cannot be edited")

    update_data = {}
    
    admin_only_fields = [
        "amount", "amount_paid", "quantity", "unit_price", "plot_size_sqm", "property_name", 
        "property_location", "property_id", "payment_terms", "sales_rep_name", 
        "sales_rep_id", "invoice_date", "co_owner_name", "co_owner_email"
    ]
    staff_allowed_fields = ["due_date", "notes"]
    
    for field, value in payload.items():
        if field in admin_only_fields:
            if role != "admin":
                raise HTTPException(status_code=403, detail=f"Permission denied to edit {field}")
            update_data[field] = value
        elif field in staff_allowed_fields:
            update_data[field] = value
            
    if not update_data:
        return {"message": "No changes applied"}

    # Special handling for due_date change logging
    if "due_date" in update_data and update_data["due_date"] != invoice.get("due_date"):
        reason = payload.get("reason")
        if not reason or len(reason) < 10:
             raise HTTPException(status_code=400, detail="A detailed reason (min 10 chars) is required for due date changes")
        
        db.table("due_date_changes").insert({
            "invoice_id": invoice_id,
            "old_date": invoice["due_date"],
            "new_date": update_data["due_date"],
            "reason": reason,
            "changed_by": current_admin["sub"]
        }).execute()

    # Update database
    db.table("invoices").update(jsonable_encoder(update_data)).eq("id", invoice_id).execute()
    log_activity(
        "invoice_edited",
        f"Invoice {invoice['invoice_number']} updated by {role}",
        current_admin["sub"],
        invoice_id=invoice_id
    )

    # Sync commissions if Sales Rep changed
    if "sales_rep_id" in update_data:
        background_tasks.add_task(
            sync_invoice_commissions,
            invoice_id=invoice_id,
            db=db,
            performed_by=current_admin["sub"]
        )
    
    return {"message": "Invoice updated successfully"}


@router.get("/{invoice_id}/html-view")
async def view_document_html(
    request: Request, 
    invoice_id: str, 
    type: str = "invoice",
    current_admin=Depends(resolve_admin_token)
):
    """Render a professional HTML view for terminal-free document viewing."""
    db = get_db()
    inv = db.table("invoices").select("*, clients(*), payments(*)").eq("id", invoice_id).execute()
    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = inv.data[0]
    is_receipt = type == "receipt" or ("Receipt" in type.title())
    
    return templates.TemplateResponse("invoice_view.html", {
        "request": request,
        "invoice": invoice,
        "is_receipt": is_receipt,
        "title": "Receipt" if is_receipt else "Invoice"
    })


@router.get("/{invoice_id}/pdf/{doc_type}")
async def download_pdf(invoice_id: str, doc_type: str, current_admin=Depends(resolve_admin_token)):
    db = get_db()
    inv = db.table("invoices")\
        .select("*, clients(*), payments(*)")\
        .eq("id", invoice_id)\
        .execute()
    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = inv.data[0]

    # Fallback for missing location data
    if not invoice.get("property_location") and invoice.get("property_name"):
        prop_res = db.table("properties").select("location").ilike("name", f"%{invoice['property_name']}%").execute()
        if prop_res.data:
            invoice["property_location"] = prop_res.data[0]["location"]

    # Look up sales rep phone from sales_reps table
    if not invoice.get("sales_rep_phone"):
        if invoice.get("sales_rep_id"):
            rep_res = db.table("sales_reps").select("phone").eq("id", invoice["sales_rep_id"]).limit(1).execute()
            if rep_res.data:
                invoice["sales_rep_phone"] = rep_res.data[0].get("phone")
        elif invoice.get("sales_rep_name"):
            rep_res = db.table("sales_reps").select("phone").eq("name", invoice["sales_rep_name"]).limit(1).execute()
            if rep_res.data:
                invoice["sales_rep_phone"] = rep_res.data[0].get("phone")

    if doc_type == "invoice":
        pdf_bytes = generate_invoice_pdf(invoice)
        filename = f"Invoice_{invoice['invoice_number']}.pdf"
    elif doc_type == "receipt":
        pdf_bytes = generate_receipt_pdf(invoice)
        filename = f"Receipt_{invoice['invoice_number']}.pdf"
    elif doc_type == "statement":
        all_inv = db.table("invoices")\
            .select("*, payments(*)")\
            .eq("client_id", invoice["client_id"])\
            .neq("status", "voided")\
            .order("invoice_date")\
            .execute()
        
        # Ensure property_location fallback for statement invoices too
        for ai in all_inv.data:
            if not ai.get("property_location") and ai.get("property_name"):
                pr = db.table("properties").select("location").ilike("name", f"%{ai['property_name']}%").execute()
                if pr.data:
                    ai["property_location"] = pr.data[0]["location"]
                    
        pdf_bytes = generate_statement_pdf(all_inv.data, invoice["clients"])
        filename = f"Statement_{invoice['clients']['full_name'].replace(' ', '_')}.pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid document type")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

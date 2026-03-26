from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from models import PaymentCreate, PaymentUpdate
from pdf_service import generate_refund_receipt_pdf
from fastapi.responses import StreamingResponse
import io

from commission_service import get_commission_rate
from email_service import send_commission_earned_email
from datetime import date

router = APIRouter()

@router.post("/")
async def record_payment(
    data: PaymentCreate, 
    background_tasks: BackgroundTasks,
    current_admin=Depends(verify_token)
):
    db = get_db()

    # Verify invoice exists
    inv = db.table("invoices").select("*").eq("id", data.invoice_id).execute()
    if not inv.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    payment_data = {
        "invoice_id": data.invoice_id,
        "client_id": data.client_id,
        "reference": data.reference,
        "amount": data.amount,
        "payment_method": data.payment_method,
        "payment_type": data.payment_type,
        "payment_date": data.payment_date,
        "notes": data.notes,
        "recorded_by": current_admin["sub"]
    }
    
    # Use jsonable_encoder to handle Decimal/date types for Supabase
    encoded_data = jsonable_encoder(payment_data)
    result = db.table("payments").insert(encoded_data).execute()

    payment_id = result.data[0]["id"]

    # --- Commission Logic (Only for Standard Payments) ---
    if data.payment_type == "payment":
        invoice = inv.data[0]
        rep_id = invoice.get("sales_rep_id")
        
        # Fallback for old invoices without sales_rep_id but have a name
        if not rep_id and invoice.get("sales_rep_name"):
            rep_name = invoice["sales_rep_name"].strip()
            rep_res = db.table("sales_reps")\
                .select("id")\
                .ilike("name", f"%{rep_name}%")\
                .eq("is_active", True)\
                .execute()
            if rep_res.data:
                rep_id = rep_res.data[0]["id"]
                
        if rep_id:
            # Calculate commission rate
            rate = get_commission_rate(
                sales_rep_id=rep_id,
                estate_name=invoice.get("property_name", ""),
                verification_date=date.today(),
                db=db
            )
            deposit = float(data.amount)
            commission_amount = round(deposit * rate / 100, 2)
            
            # Fetch client for email payload
            client_res = db.table("clients").select("*").eq("id", data.client_id).execute()
            client_data = client_res.data[0] if client_res.data else {}
            
            # Insert standard commission earning
            earning = db.table("commission_earnings").insert({
                "sales_rep_id": rep_id,
                "invoice_id": invoice["id"],
                "payment_id": payment_id,
                "client_id": data.client_id,
                "estate_name": invoice.get("property_name", ""),
                "payment_amount": deposit,
                "commission_rate": rate,
                "commission_amount": commission_amount,
            }).execute().data[0]
            
            # Send email
            rep_res = db.table("sales_reps").select("*").eq("id", rep_id).execute()
            if rep_res.data:
                background_tasks.add_task(
                    send_commission_earned_email,
                    rep=rep_res.data[0],
                    client=client_data,
                    invoice=invoice,
                    earning=earning
                )
    # -----------------------------------------------------

    background_tasks.add_task(
        log_activity,
        "payment_recorded" if data.payment_type == "payment" else "refund_recorded",
        f"{data.payment_type.title()} of NGN {data.amount:,.2f} recorded for {inv.data[0]['invoice_number']}",
        current_admin["sub"],
        client_id=data.client_id,
        invoice_id=data.invoice_id
    )

    inv_num = inv.data[0].get('invoice_number', 'N/A')
    return {"message": "Payment recorded", "payment": result.data[0], "invoice_number": inv_num}


@router.get("/invoice/{invoice_id}")
async def get_payments_for_invoice(invoice_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("payments")\
        .select("*")\
        .eq("invoice_id", invoice_id)\
        .order("payment_date")\
        .execute()
    return result.data
@router.patch("/{payment_id}")
async def update_payment(
    payment_id: str,
    data: PaymentUpdate,
    current_admin=Depends(verify_token)
):
    db = get_db()
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can edit payments")
    
    # 1. Fetch current payment to get invoice_id
    pay_res = db.table("payments").select("*").eq("id", payment_id).execute()
    if not pay_res.data:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = pay_res.data[0]
    invoice_id = payment["invoice_id"]
    
    # 2. Update payment
    update_data = jsonable_encoder(data, exclude_none=True)
    if not update_data:
        return {"message": "No changes applied"}
        
    db.table("payments").update(update_data).eq("id", payment_id).execute()
    
    # 3. Recalculate invoice (Note: The DB trigger 'after_payment_update' in schema.sql 
    # should already handle this, but we'll log it)
    inv_res = db.table("invoices").select("invoice_number").eq("id", invoice_id).execute()
    inv_num = inv_res.data[0]["invoice_number"] if inv_res.data else "N/A"
    
    log_activity(
        "payment_edited",
        f"Payment of NGN {payment['amount']} for invoice {inv_num} updated by Admin",
        current_admin["sub"],
        invoice_id=invoice_id
    )
    
    return {"message": "Payment updated successfully"}


@router.get("/{payment_id}/pdf/refund")
async def download_refund_receipt(payment_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    
    # 1. Fetch payment
    pay_res = db.table("payments").select("*").eq("id", payment_id).execute()
    if not pay_res.data:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = pay_res.data[0]
    if payment.get("payment_type") != "refund":
        raise HTTPException(status_code=400, detail="This transaction is not a refund")
        
    # 2. Fetch invoice and client
    inv_res = db.table("invoices")\
        .select("*, clients(*)")\
        .eq("id", payment["invoice_id"])\
        .execute()
    
    if not inv_res.data:
        raise HTTPException(status_code=404, detail="Linked invoice not found")
        
    invoice = inv_res.data[0]
    
    # 3. Generate PDF
    pdf_bytes = generate_refund_receipt_pdf(payment, invoice)
    filename = f"Refund_Receipt_{invoice['invoice_number']}_{payment['reference']}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

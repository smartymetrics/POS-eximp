from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from models import PaymentCreate, PaymentUpdate
from pdf_service import generate_refund_receipt_pdf
from fastapi.responses import StreamingResponse
import io

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

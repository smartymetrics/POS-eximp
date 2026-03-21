from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from models import PaymentCreate

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
    
    result = db.table("payments").insert({
        "invoice_id": data.invoice_id,
        "client_id": data.client_id,
        "reference": data.reference,
        "amount": float(data.amount),
        "payment_method": data.payment_method,
        "payment_date": str(data.payment_date),
        "notes": data.notes,
        "recorded_by": current_admin["sub"]
    }).execute()

    background_tasks.add_task(
        log_activity,
        "payment_recorded",
        f"Payment of NGN {data.amount:,.2f} recorded for {inv.data[0]['invoice_number']}",
        current_admin["sub"],
        client_id=data.client_id,
        invoice_id=data.invoice_id
    )

    return {"message": "Payment recorded", "payment": result.data[0]}


@router.get("/invoice/{invoice_id}")
async def get_payments_for_invoice(invoice_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("payments")\
        .select("*")\
        .eq("invoice_id", invoice_id)\
        .order("payment_date")\
        .execute()
    return result.data

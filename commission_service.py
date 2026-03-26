import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

def get_commission_rate(sales_rep_id: str, estate_name: str, verification_date: date, db) -> float:
    """
    Determines the applicable commission rate for a rep at a specific date and estate.
    1. Check for specific rate override in commission_rates table.
    2. Fallback to rep's profile default.
    3. Final fallback to system-wide default.
    """
    # 1. Check for specific rate override for this rep + estate + date
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

    # 2. Fallback to the rep's profile default rate
    rep_res = db.table("sales_reps").select("commission_rate").eq("id", sales_rep_id).execute()
    if rep_res.data and rep_res.data[0].get("commission_rate") is not None:
        return float(rep_res.data[0]["commission_rate"])

    # 3. Final fallback to system-wide default
    default = db.table("system_settings")\
        .select("value")\
        .eq("key", "default_commission_rate")\
        .execute()
    return float(default.data[0]["value"]) if default.data else 5.0

async def sync_invoice_commissions(invoice_id: str, db, performed_by: str = "system"):
    """
    Scans all verified payments for an invoice and ensures a commission_earnings record
    exists for the current sales rep assigned to the invoice.
    """
    from routers.analytics import log_activity
    from email_service import send_commission_earned_email
    
    # 1. Fetch current invoice state
    inv_res = db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute()
    if not inv_res.data:
        logger.error(f"Sync failed: Invoice {invoice_id} not found")
        return
        
    invoice = inv_res.data[0]
    client = invoice.get("clients")
    rep_id = invoice.get("sales_rep_id")
    
    if not rep_id:
        logger.info(f"Sync skipped: Invoice {invoice['invoice_number']} has no sales rep assigned.")
        return

    # 2. Fetch Sales Rep details for notification
    rep_res = db.table("sales_reps").select("*").eq("id", rep_id).execute()
    if not rep_res.data:
        logger.error(f"Sync failed: Sales rep {rep_id} not found")
        return
    rep = rep_res.data[0]

    # 3. Fetch all non-voided payments for this invoice
    payments = db.table("payments")\
        .select("*")\
        .eq("invoice_id", invoice_id)\
        .eq("is_voided", False)\
        .eq("payment_type", "payment")\
        .execute().data or []
        
    synced_count = 0
    
    for pay in payments:
        # Check if a non-voided commission record already exists for this payment
        existing = db.table("commission_earnings")\
            .select("id, sales_rep_id")\
            .eq("payment_id", pay["id"])\
            .eq("is_voided", False)\
            .execute().data
            
        if existing:
            # If it already belongs to the current rep, skip
            if existing[0]["sales_rep_id"] == rep_id:
                continue
            
            # If it belongs to a different rep, we void the old one and create a new one?
            # Or just update? Let's void for clear audit trail if it was a mistake.
            db.table("commission_earnings").update({
                "is_voided": True,
                "void_reason": f"Commission re-assigned during invoice update to {rep['name']}",
                "voided_by": performed_by,
                "voided_at": datetime.now().isoformat()
            }).eq("id", existing[0]["id"]).execute()
            
        # Create new commission record
        rate = get_commission_rate(
            sales_rep_id=rep_id,
            estate_name=invoice["property_name"],
            verification_date=date.fromisoformat(pay["payment_date"]),
            db=db
        )
        
        amount = float(pay["amount"])
        commission_amount = round(amount * rate / 100, 2)
        
        earning = db.table("commission_earnings").insert({
            "sales_rep_id": rep_id,
            "invoice_id": invoice_id,
            "payment_id": pay["id"],
            "client_id": invoice["client_id"],
            "estate_name": invoice["property_name"],
            "payment_amount": amount,
            "commission_rate": rate,
            "commission_amount": commission_amount,
            "created_at": pay["created_at"] # Match original payment timing
        }).execute().data[0]
        
        synced_count += 1
        
        # Notify the new rep
        try:
            from email_service import send_commission_earned_email
            await send_commission_earned_email(
                rep=rep,
                client=client,
                invoice=invoice,
                earning=earning
            )
        except Exception as e:
            logger.error(f"Failed to send commission notification during sync: {e}")

    if synced_count > 0:
        await log_activity(
            "commission_synced",
            f"Successfully synced {synced_count} commission records for Invoice {invoice['invoice_number']} to {rep['name']}",
            performed_by,
            invoice_id=invoice_id,
            client_id=invoice["client_id"]
        )

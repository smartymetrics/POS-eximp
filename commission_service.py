import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

def get_commission_config(sales_rep_id: str, estate_name: str, verification_date: date, db) -> dict:
    """
    Determines the applicable commission configuration (Gross Rate, WHT Rate).
    Returns: {"gross_rate": float, "wht_rate": float}
    """
    # 1. Check for specific rate override in commission_rates table
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
        return {"gross_rate": float(result.data[0]["rate"]), "wht_rate": 5.0}

    # 2. Check Sales Rep Profile
    rep_res = db.table("sales_reps").select("gross_commission_rate, wht_rate").eq("id", sales_rep_id).execute()
    if rep_res.data:
        r = rep_res.data[0]
        return {
            "gross_rate": float(r.get("gross_commission_rate") or 10.0),
            "wht_rate": float(r.get("wht_rate") or 5.0)
        }

    # 3. Check if this is a Vendor Partner
    vendor_res = db.table("vendors").select("gross_commission_rate, wht_rate").eq("id", sales_rep_id).eq("is_commission_partner", True).execute()
    if vendor_res.data:
        v = vendor_res.data[0]
        return {
            "gross_rate": float(v.get("gross_commission_rate") or 15.0),
            "wht_rate": float(v.get("wht_rate") or 5.0)
        }

    return {"gross_rate": 10.0, "wht_rate": 5.0}

def get_commission_rate(sales_rep_id: str, estate_name: str, verification_date: date, db) -> float:
    """Compatibility alias for get_commission_config returning just the gross rate."""
    config = get_commission_config(sales_rep_id, estate_name, verification_date, db)
    return config["gross_rate"]

async def sync_invoice_commissions(invoice_id: str, db, performed_by: str = "system"):
    """
    Ensures that every active (non-voided) payment for an invoice has exactly 
    one active commission earning record for the current assigned sales rep.
    1. Voids existing active commissions that are now 'orphaned' (payment voided/deleted).
    2. Voids commissions assigned to the wrong rep.
    3. Greated missing commissions for active payments.
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
        # If no rep assigned, void all unpaid commissions for this invoice
        db.table("commission_earnings").update({
            "is_voided": True,
            "void_reason": "No sales rep assigned to invoice",
            "voided_by": performed_by,
            "voided_at": datetime.now().isoformat()
        }).eq("invoice_id", invoice_id).eq("is_voided", False).eq("is_paid", False).execute()
        return

    # 2. Fetch Sales Rep details for notification
    rep_res = db.table("sales_reps").select("*").eq("id", rep_id).execute()
    if not rep_res.data:
        logger.error(f"Sync failed: Sales rep {rep_id} not found")
        return
    rep = rep_res.data[0]

    # 3. Fetch all active earnings for this invoice
    earnings = db.table("commission_earnings")\
        .select("*")\
        .eq("invoice_id", invoice_id)\
        .eq("is_voided", False)\
        .execute().data or []
        
    # 4. Fetch all active payments for this invoice
    active_payments = db.table("payments")\
        .select("*")\
        .eq("invoice_id", invoice_id)\
        .eq("is_voided", False)\
        .eq("payment_type", "payment")\
        .execute().data or []
    
    active_pay_ids = {p["id"] for p in active_payments}
    
    # 5. VOID orphaned or misassigned commissions
    voided_count = 0
    remaining_earnings_map = {} # payment_id -> earning_record
    
    for e in earnings:
        is_orphaned = e["payment_id"] not in active_pay_ids
        is_misassigned = e["sales_rep_id"] != rep_id
        
        if is_orphaned or is_misassigned:
            if not e["is_paid"]:
                db.table("commission_earnings").update({
                    "is_voided": True,
                    "void_reason": "Associated payment voided/rejected" if is_orphaned else f"Re-assigned to {rep['name']}",
                    "voided_by": performed_by,
                    "voided_at": datetime.now().isoformat()
                }).eq("id", e["id"]).execute()
                voided_count += 1
                logger.info(f"Sync: Voided earning {e['id']} (orphaned={is_orphaned}, misassigned={is_misassigned})")
            else:
                logger.info(f"Sync: Cannot void already PAID commission {e['id']} for payment {e['payment_id']}")
        else:
            remaining_earnings_map[e["payment_id"]] = e

    # 6. SYNC missing commissions for active payments
    synced_count = 0
    for pay in active_payments:
        if pay["id"] in remaining_earnings_map:
            continue
            
        # Create new commission record
        config = get_commission_config(
            sales_rep_id=rep_id,
            estate_name=invoice["property_name"],
            verification_date=date.fromisoformat(pay["payment_date"]),
            db=db
        )
        
        pay_amt = float(pay["amount"])
        gross_comm = round(pay_amt * config["gross_rate"] / 100, 2)
        wht_amt = round(gross_comm * config["wht_rate"] / 100, 2)
        net_comm = gross_comm - wht_amt
        
        earning = db.table("commission_earnings").insert({
            "sales_rep_id": rep_id,
            "invoice_id": invoice_id,
            "payment_id": pay["id"],
            "client_id": invoice["client_id"],
            "estate_name": invoice["property_name"],
            "payment_amount": pay_amt,
            "commission_rate": config["gross_rate"],
            "commission_amount": net_comm, # Still keep this for backward compat
            "gross_commission": gross_comm,
            "wht_amount": wht_amt,
            "net_commission": net_comm,
            "created_at": pay["created_at"]
        }).execute().data[0]
        
        synced_count += 1
        
        # Notify the rep
        try:
            await send_commission_earned_email(
                rep=rep,
                client=client,
                invoice=invoice,
                earning=earning
            )
        except Exception as e:
            logger.error(f"Failed to send commission notification during sync: {e}")

    if synced_count > 0 or voided_count > 0:
        msg = f"Synced commissions for Invoice {invoice['invoice_number']}: {synced_count} added, {voided_count} voided."
        await log_activity(
            "commission_synced",
            msg,
            performed_by,
            invoice_id=invoice_id,
            client_id=invoice["client_id"]
        )
        logger.info(msg)

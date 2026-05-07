
from database import get_db, db_execute
import asyncio

async def check_and_fix():
    db = get_db()
    invoice_id = "78fb6477-7a08-477c-9aac-13d0bd56e799" # EC-000021
    
    # 1. Get invoice and client
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("id", invoice_id).execute())
    inv = inv_res.data[0]
    
    # 2. Get the 400k payment
    pmts_res = await db_execute(lambda: db.table("payments")
        .select("*")
        .eq("invoice_id", invoice_id)
        .eq("amount", 400000)
        .eq("is_voided", False)
        .execute()
    )
    if not pmts_res.data:
        print("400k payment not found.")
        return
    pmt = pmts_res.data[0]
    
    # 3. Get the expenditure request
    reqs_res = await db_execute(lambda: db.table("expenditure_requests")
        .select("*")
        .eq("vendor_invoice_number", "EC-000021")
        .eq("payment_type", "instalment")
        .execute()
    )
    if not reqs_res.data:
        print("No instalment request found.")
        return
    req = reqs_res.data[0]
    
    # 4. Create ledger entry
    ledger_payload = {
        "invoice_id": invoice_id,
        "payment_id": pmt["id"],
        "client_id": inv["client_id"],
        "estate_name": inv["property_name"],
        "payment_amount": pmt["amount"],
        "commission_rate": 0.1, # 10%
        "commission_amount": req["amount_gross"],
        "gross_commission": req["amount_gross"],
        "net_commission": req["net_payout_amount"],
        "wht_amount": req["wht_amount"],
        "is_paid": True,
        "paid_at": req.get("paid_at") or req.get("created_at"),
        "vendor_id": req["vendor_id"],
        "payout_reference": req.get("payout_reference")
    }
    
    # Try to find sales_rep_id
    vendor_res = await db_execute(lambda: db.table("vendors").select("admin_id").eq("id", req["vendor_id"]).execute())
    if vendor_res.data:
        ledger_payload["sales_rep_id"] = vendor_res.data[0].get("admin_id")
    
    await db_execute(lambda: db.table("commission_earnings").insert(ledger_payload).execute())
    print("✓ Commission ledger entry created.")

if __name__ == "__main__":
    asyncio.run(check_and_fix())

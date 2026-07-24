
from database import get_db, db_execute
import asyncio
import json

async def check_invoice_payments(invoice_number):
    db = get_db()
    
    # 1. Get invoice ID
    inv_res = await db_execute(lambda: db.table("invoices").select("id, invoice_number").eq("invoice_number", invoice_number).execute())
    if not inv_res.data:
        print(f"Invoice {invoice_number} not found.")
        return
    
    inv_id = inv_res.data[0]["id"]
    print(f"Checking Invoice: {invoice_number} (ID: {inv_id})")
    
    # 2. Get all payments for this invoice
    pmt_res = await db_execute(lambda: db.table("payments").select("*").eq("invoice_id", inv_id).execute())
    payments = pmt_res.data
    
    print(f"\nFound {len(payments)} total payments in DB:")
    for p in payments:
        print(f"- ID: {p['id']}, Amount: {p['amount']}, Method: {p['payment_method']}, Voided: {p.get('is_voided')}, Date: {p.get('created_at')}")

    # 3. Get all commission earnings for this invoice
    comm_res = await db_execute(lambda: db.table("commission_earnings").select("*").eq("invoice_id", inv_id).execute())
    print(f"\nFound {len(comm_res.data)} commission earnings records:")
    for c in comm_res.data:
        print(f"- ID: {c['id']}, Amount: {c['amount_gross']}, Payment ID: {c.get('payment_id')}, Status: {'Paid' if c.get('is_paid') else 'Unpaid'}")

    # 4. Get all expenditure requests for this invoice
    exp_res = await db_execute(lambda: db.table("expenditure_requests").select("*").eq("vendor_invoice_number", invoice_number).execute())
    print(f"\nFound {len(exp_res.data)} expenditure requests (portal claims):")
    for e in exp_res.data:
        print(f"- ID: {e['id']}, Amount: {e['amount_gross']}, Status: {e['status']}, Type: {e.get('payment_type')}")

if __name__ == "__main__":
    import sys
    inv_num = sys.argv[1] if len(sys.argv) > 1 else "EC-000021"
    asyncio.run(check_invoice_payments(inv_num))

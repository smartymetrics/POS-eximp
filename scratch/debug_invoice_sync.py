
import sys
import os
sys.path.append(os.getcwd())
import asyncio
from database import get_db, db_execute

async def check_invoice():
    db = get_db()
    
    # 1. Check Invoice
    inv_res = await db_execute(lambda: db.table('invoices').select('id, amount, amount_paid, status, sales_rep_id').eq('invoice_number', 'EC-000025').execute())
    if not inv_res.data:
        print("Invoice EC-000025 not found")
        return
    
    inv = inv_res.data[0]
    inv_id = inv['id']
    print(f"Invoice: {inv}")
    
    # 2. Check Commission Earnings
    comm_res = await db_execute(lambda: db.table('commission_earnings').select('*').eq('invoice_id', inv_id).execute())
    print(f"Commission Earnings for Invoice {inv_id}:")
    for c in comm_res.data:
        print(f"  - ID: {c['id']}, Amount: {c['commission_amount']}, Paid: {c['amount_paid']}, Is Paid: {c['is_paid']}")
    
    # 3. Check Expenditure Requests (Claims)
    exp_res = await db_execute(lambda: db.table('expenditure_requests').select('*').eq('invoice_id', inv_id).execute())
    print(f"Expenditure Requests for Invoice {inv_id}:")
    for e in exp_res.data:
        print(f"  - ID: {e['id']}, Amount: {e['amount_gross']}, Status: {e['status']}, Paid: {e['amount_paid']}")

if __name__ == "__main__":
    asyncio.run(check_invoice())

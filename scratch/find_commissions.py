import asyncio
from database import get_db, db_execute

async def main():
    db = get_db()
    
    # Get invoices IDs
    inv_res = await db_execute(lambda: db.table("invoices").select("id, invoice_number").in_("invoice_number", ["EC-000061", "EC-000025"]).execute())
    invs = inv_res.data or []
    inv_ids = [i["id"] for i in invs]
    inv_map = {i["id"]: i["invoice_number"] for i in invs}
    print(f"Invoices found: {invs}")
    
    # Query commission_earnings
    comm_res = await db_execute(lambda: db.table("commission_earnings").select(
        "id, invoice_id, commission_amount, final_amount, amount_paid, is_paid"
    ).in_("invoice_id", inv_ids).execute())
    comms = comm_res.data or []
    
    print("\nCommissions found:")
    for c in comms:
        print(f"  - Comm ID: {c['id']} | Invoice: {inv_map.get(c['invoice_id'])} | Final: {float(c.get('final_amount') or 0):,.2f} | Paid: {float(c.get('amount_paid') or 0):,.2f} | is_paid: {c['is_paid']}")

    # Query expenditure_requests
    exp_res = await db_execute(lambda: db.table("expenditure_requests").select(
        "id, invoice_id, title, category, amount_gross, status"
    ).in_("invoice_id", inv_ids).execute())
    exps = exp_res.data or []
    print("\nExpenditures found:")
    for e in exps:
        print(f"  - Exp ID: {e['id']} | Invoice: {inv_map.get(e['invoice_id'])} | Title: {e['title']} | Category: {e['category']} | Status: {e['status']}")

if __name__ == "__main__":
    asyncio.run(main())

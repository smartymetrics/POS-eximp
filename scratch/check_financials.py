import asyncio
from database import get_db, db_execute

async def main():
    db = get_db()
    
    # Select some paid commission expenditure requests
    res = await db_execute(lambda: db.table("expenditure_requests").select(
        "id, title, amount_gross, net_payout_amount, amount_paid, status"
    ).eq("status", "paid").in_("category", ["Sales Commission", "Partner Payout"]).execute())
    
    print("Paid expenditures info:")
    for r in res.data or []:
        print(f"  - {r['title']} | Gross: {r['amount_gross']} | Net: {r['net_payout_amount']} | Paid: {r['amount_paid']}")

if __name__ == "__main__":
    asyncio.run(main())

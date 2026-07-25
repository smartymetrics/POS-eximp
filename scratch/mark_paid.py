import asyncio
from datetime import datetime
from database import get_db, db_execute

async def main():
    db = get_db()
    now_str = datetime.now().isoformat()
    
    print("Updating remaining expenditure request...")
    res = await db_execute(lambda: db.table("expenditure_requests").update({
        "status": "paid",
        "amount_paid": 19000.0,
        "paid_at": now_str,
        "payout_reference": "DIRECT-PAY"
    }).eq("id", "cf4ef014-929e-4b14-ba58-2ec198896d2d").execute())
    
    print("Done! Number of records updated:", len(res.data or []))

if __name__ == "__main__":
    asyncio.run(main())

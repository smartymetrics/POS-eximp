
from database import get_db, db_execute
import asyncio

async def check_schema():
    db = get_db()
    res = await db_execute(lambda: db.table("commission_earnings").select("*").limit(1).execute())
    if res.data:
        print(f"Columns: {list(res.data[0].keys())}")
    else:
        print("No records in commission_earnings.")

if __name__ == "__main__":
    asyncio.run(check_schema())

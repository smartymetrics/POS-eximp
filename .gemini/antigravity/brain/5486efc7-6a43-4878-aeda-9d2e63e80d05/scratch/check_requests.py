import asyncio
import sys
import os
sys.path.append(os.getcwd())
from database import get_db, db_execute
import json

async def check():
    db = get_db()
    res = await db_execute(lambda: db.table("sales_reps").select("name, wht_rate").limit(5).execute())
    print("Sales Rep Rates:", res.data)
    
    res2 = await db_execute(lambda: db.table("commission_earnings").select("wht_amount, wht_rate, gross_commission").limit(5).execute())
    print("Commission Rates:", res2.data)

if __name__ == "__main__":
    asyncio.run(check())

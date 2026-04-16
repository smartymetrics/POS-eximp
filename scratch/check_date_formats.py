
import os
import sys
import asyncio

# Add root to sys.path
sys.path.append(os.getcwd())

from database import get_db, db_execute

async def check_dates():
    db = get_db()
    res = await db_execute(lambda: db.table("staff_profiles").select("dob, date_joined").limit(10).execute())
    if res.data:
        for i, row in enumerate(res.data):
            print(f"Row {i}: dob='{row.get('dob')}', date_joined='{row.get('date_joined')}'")
    else:
        print("No staff profiles found.")

if __name__ == "__main__":
    asyncio.run(check_dates())

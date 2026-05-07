import asyncio
import sys
import os
sys.path.append(os.getcwd())
from database import get_db, db_execute
import json

async def check():
    db = get_db()
    res = await db_execute(lambda: db.table("staff_profiles").select("*").limit(1).execute())
    if res.data:
        print("Staff Profile Columns:", res.data[0].keys())
    else:
        print("No staff profiles found.")

if __name__ == "__main__":
    asyncio.run(check())

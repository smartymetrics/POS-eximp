import asyncio
import sys
import os
sys.path.append(os.getcwd())
from database import get_db, db_execute
import json

async def check():
    db = get_db()
    res = await db_execute(lambda: db.table("expenditure_requests").select("id, status, title").ilike("title", "%EC-000021%").execute())
    print("Found Requests:", res.data)

if __name__ == "__main__":
    asyncio.run(check())

import sys
import os
sys.path.append(os.getcwd())
from database import get_db
import asyncio
import json

async def check():
    db = get_db()
    from database import db_execute
    try:
        res = await db_execute(lambda: db.table('expenditure_requests').select('id, title, description, category, requester_id, payout_method, vendor_id, vendors(name, type), created_at').order('created_at', desc=True).limit(30).execute())
        print(json.dumps(res.data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())

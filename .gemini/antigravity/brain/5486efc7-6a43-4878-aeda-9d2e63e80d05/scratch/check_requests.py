import asyncio
import sys
import os
sys.path.append(os.getcwd())
from database import get_db, db_execute
import json

async def check():
    db = get_db()
    res = await db_execute(lambda: db.table('expenditure_requests')
        .select('id, title, status, vendor_id, invoice_id, payment_id, vendors(name)')
        .neq('status', 'voided')
        .order('created_at', desc=True)
        .limit(10)
        .execute())
    
    print(json.dumps(res.data, indent=2))

if __name__ == "__main__":
    asyncio.run(check())

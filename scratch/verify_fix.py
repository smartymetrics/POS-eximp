
from database import get_db, db_execute
from routers.payouts import portal_lookup_invoice
import asyncio
import json

async def verify():
    try:
        res = await portal_lookup_invoice("EC-000021")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify())

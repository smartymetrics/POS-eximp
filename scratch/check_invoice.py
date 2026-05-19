import asyncio
import os
import sys
import json
sys.path.append(os.getcwd())
from database import get_db, db_execute

async def main():
    db = get_db()
    invoice_number = "EC-000033"
    try:
        res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("invoice_number", invoice_number).execute())
        if res.data:
            print("Found invoice in database:")
            print(json.dumps(res.data[0], indent=2, default=str))
        else:
            print(f"Invoice {invoice_number} not found in database.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

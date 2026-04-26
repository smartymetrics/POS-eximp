
import asyncio
import os
import sys
sys.path.append(os.getcwd())
from database import get_db, db_execute

async def main():
    db = get_db()
    try:
        # We can try to list all tables by querying information_schema.tables if available via RPC,
        # or we can just try to select from 'inventory_assets', 'assets', 'inventory' to see if they exist.
        for t in ["assets", "inventory", "inventory_assets", "company_assets"]:
            try:
                res = await db_execute(lambda: db.table(t).select("*").limit(1).execute())
                print(f"Table '{t}' exists. Columns: {list(res.data[0].keys()) if res.data else 'Empty table'}")
            except Exception as e:
                pass
                
        print("Check finished.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

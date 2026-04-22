from database import get_db, db_execute
import asyncio
import json

async def check_assets():
    db = get_db()
    # Check company_assets
    res = await db_execute(lambda: db.table("company_assets").select("*").limit(5).execute())
    print(f"--- Company Assets ({len(res.data)} records) ---")
    print(json.dumps(res.data, indent=2))
    
    # Check if there's an asset_inventory table
    try:
        res2 = await db_execute(lambda: db.table("asset_inventory").select("*").limit(5).execute())
        print(f"\n--- Asset Inventory ({len(res2.data)} records) ---")
        print(json.dumps(res2.data, indent=2))
    except:
        print("\n--- No table named 'asset_inventory' found ---")

if __name__ == "__main__":
    asyncio.run(check_assets())

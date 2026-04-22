from database import get_db, db_execute
import asyncio
import json

async def check_properties():
    db = get_db()
    res = await db_execute(lambda: db.table("properties").select("name, starting_price").limit(5).execute())
    print(f"--- Properties ({len(res.data)} records) ---")
    print(json.dumps(res.data, indent=2))

if __name__ == "__main__":
    asyncio.run(check_properties())

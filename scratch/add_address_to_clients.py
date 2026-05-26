import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, db_execute

async def main():
    db = get_db()
    
    # Add address column to clients table
    sql = "ALTER TABLE clients ADD COLUMN IF NOT EXISTS address TEXT;"
    try:
        res = await db_execute(lambda: db.rpc("exec_sql", {"sql_body": sql}).execute())
        print(f"address column added: {res.data}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Verify by checking a client row
    try:
        res = await db_execute(lambda: db.table("clients").select("id, address, occupation, city, state, lead_source").limit(1).execute())
        print(f"Sample client row keys: {list(res.data[0].keys()) if res.data else 'No rows'}")
    except Exception as e:
        print(f"Verify failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

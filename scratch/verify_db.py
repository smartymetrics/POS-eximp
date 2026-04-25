
import asyncio
import os
import sys
sys.path.append(os.getcwd())
from database import get_db, db_execute

async def main():
    db = get_db()
    try:
        # Check if rejection_reason exists
        res = await db_execute(lambda: db.table("expenditure_requests").select("rejection_reason").limit(1).execute())
        print("Column 'rejection_reason' already exists.")
    except Exception as e:
        if "column \"rejection_reason\" does not exist" in str(e):
            print("Column 'rejection_reason' is MISSING. Attempting to create via RPC...")
            try:
                # Try exec_sql RPC if it exists
                sql = "ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS rejection_reason TEXT;"
                await db_execute(lambda: db.rpc("exec_sql", {"sql_query": sql}).execute())
                print("Successfully created column via RPC!")
            except Exception as e2:
                print(f"RPC failed: {e2}")
                print("Please run the following SQL in Supabase SQL Editor:")
                print("ALTER TABLE expenditure_requests ADD COLUMN IF NOT EXISTS rejection_reason TEXT;")
        else:
            print(f"Error checking column: {e}")

if __name__ == "__main__":
    asyncio.run(main())

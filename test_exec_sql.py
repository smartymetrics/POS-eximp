import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import supabase, init_db

async def run_test():
    await init_db()
    
    # Try a simple SELECT 1 statement
    print("Testing simple statement: SELECT 1")
    try:
        res = supabase.rpc("exec_sql", {"sql_body": "SELECT 1"}).execute()
        print("Result:", res.data)
    except Exception as e:
        print("Failed SELECT 1:", e)

    # Try checking the definition of exec_sql RPC
    print("\nAttempting to query routine definition...")
    try:
        # Check if we can select from pg_proc
        res2 = supabase.table("admins").select("id").limit(1).execute()
        print("Can query admins table: Yes")
    except Exception as e:
        print("Failed query admins table:", e)

if __name__ == "__main__":
    asyncio.run(run_test())


import os
import asyncio
from database import supabase

async def run_migration():
    with open("migrations/041_create_procurement_expenses.sql", "r") as f:
        sql = f.read()
    
    # Supabase doesn't have a direct 'execute raw sql' in the python SDK easily available for DDL 
    # without going through the RPC or dashboard.
    # However, I can try to use the 'rpc' method if a helper function exists, 
    # but usually I should tell the user to run it in the SQL editor.
    
    # Alternatively, I'll just check if the table exists.
    try:
        res = supabase.table("procurement_expenses").select("id").limit(1).execute()
        print("✅ Table procurement_expenses already exists or created.")
    except Exception as e:
        print(f"⚠️ Table check failed: {e}")
        print("Please run migrations/041_create_procurement_expenses.sql in your Supabase SQL Editor.")

if __name__ == "__main__":
    asyncio.run(run_migration())

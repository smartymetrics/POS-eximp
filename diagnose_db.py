import os
from database import get_db
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def diagnose_db():
    print("--- DB DIAGNOSTIC ---")
    db = get_db()
    
    try:
        # 1. Check if invoices table exists and get its columns
        print("Checking 'invoices' table...")
        res = db.rpc("get_table_columns", {"t_name": "invoices"}).execute()
        # Note: Need to verify if the RPC exists, if not use a regular query
    except:
        # Fallback to direct information_schema query via execution
        # Supabase Python SDK doesn't allow direct SQL by default, 
        # but we can try a select on a system table if RLS allows, 
        # but usually it doesn't.
        
        # Instead, let's just try to select the column specifically
        try:
            print("Try selecting 'sales_rep_name' from 'invoices'...")
            res = db.table("invoices").select("sales_rep_name").limit(1).execute()
            print("✅ SUCCESS: 'sales_rep_name' exists and is accessible.")
        except Exception as e:
            print(f"❌ FAIL: {e}")
            
    try:
        print("\nChecking 'activity_log' table...")
        res = db.table("activity_log").select("id").limit(1).execute()
        print("✅ SUCCESS: 'activity_log' exists.")
    except Exception as e:
        print(f"❌ FAIL: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_db())

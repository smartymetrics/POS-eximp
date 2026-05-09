
import os
import asyncio
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

async def check_payroll_schema():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Get a single row to see columns
    try:
        res = supabase.table("payroll_records").select("*").limit(1).execute()
        if res.data and len(res.data) > 0:
            print("Columns:", list(res.data[0].keys()))
        else:
            print("No data in payroll_records table to check schema via data.")
    except Exception as e:
         print("Error:", str(e))

if __name__ == "__main__":
    asyncio.run(check_payroll_schema())

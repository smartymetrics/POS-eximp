
import os
import asyncio
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

async def check_schema():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Get a single row to see columns
    res = supabase.table("properties").select("*").limit(1).execute()
    if res.data:
        print("Columns:", list(res.data[0].keys()))
    else:
        print("No data in properties table to check schema.")

if __name__ == "__main__":
    asyncio.run(check_schema())


import os
import asyncio
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

async def check_staff_schema():
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    res = supabase.table("staff_profiles").select("*").limit(1).execute()
    if res.data:
        print("Staff Profile Columns:", list(res.data[0].keys()))
    else:
        print("No staff profiles found.")

if __name__ == "__main__":
    asyncio.run(check_staff_schema())

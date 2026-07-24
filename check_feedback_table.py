import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import supabase, init_db

async def check():
    await init_db()
    try:
        res = supabase.table("client_feedback").select("id").limit(1).execute()
        print("SUCCESS: client_feedback table exists and is accessible!")
        print("Data:", res.data)
    except Exception as e:
        print("ERROR: client_feedback table does not exist or failed to query:", e)

if __name__ == "__main__":
    asyncio.run(check())

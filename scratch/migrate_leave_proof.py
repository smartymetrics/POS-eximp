import os, sys
sys.path.append(os.getcwd())
from database import get_db
import asyncio

async def run_migration():
    db = get_db()
    try:
        # Use exec_sql RPC if available, or just try to run it
        sql = "ALTER TABLE leave_requests ADD COLUMN IF NOT EXISTS proof_url TEXT;"
        res = db.rpc("exec_sql", {"sql_body": sql}).execute()
        print("Migration successful:", res.data)
    except Exception as e:
        print("Migration failed (expected if exec_sql doesn't exist):", e)
        print("Please run manually: ALTER TABLE leave_requests ADD COLUMN IF NOT EXISTS proof_url TEXT;")

if __name__ == "__main__":
    asyncio.run(run_migration())

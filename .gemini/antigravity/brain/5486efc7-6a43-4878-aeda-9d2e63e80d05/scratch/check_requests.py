import asyncio
import sys
import os
sys.path.append(os.getcwd())
from database import get_db, db_execute
import json

async def check():
    db = get_db()
    res = await db_execute(lambda: db.rpc("exec_sql", {"sql_body": "SELECT column_name FROM information_schema.columns WHERE table_name = 'commission_earnings'"}).execute())
    print("Commission Columns:", [r["column_name"] for r in res.data])

if __name__ == "__main__":
    asyncio.run(check())

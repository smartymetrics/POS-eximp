import asyncio
import os
import sys

# Ensure imports work from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, db_execute

async def main():
    db = get_db()
    sql = "ALTER TABLE legal_matters ADD COLUMN IF NOT EXISTS requires_signing BOOLEAN DEFAULT TRUE;"
    try:
        res = await db_execute(lambda: db.rpc("exec_sql", {"sql_body": sql}).execute())
        print(f"Success: {res.data}")
    except Exception as e:
        print(f"Failed via exec_sql: {e}")

if __name__ == "__main__":
    asyncio.run(main())


import asyncio
import os
import sys
sys.path.append(os.getcwd())
from database import get_db, db_execute

async def main():
    db = get_db()
    try:
        res = await db_execute(lambda: db.table("expenditure_requests").select("*").limit(1).execute())
        if res.data:
            print("Columns:", list(res.data[0].keys()))
        else:
            print("No data in expenditure_requests to infer schema.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

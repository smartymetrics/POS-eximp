
import asyncio
import os
import sys
sys.path.append(os.getcwd())
from database import get_db, db_execute

async def main():
    db = get_db()
    try:
        # Get one record and check keys
        res = await db_execute(lambda: db.table("expenditure_requests").select("*").limit(1).execute())
        if res.data:
            print("Columns found in expenditure_requests:")
            for col in res.data[0].keys():
                print(f"- {col}")
        else:
            print("No data found to check columns.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

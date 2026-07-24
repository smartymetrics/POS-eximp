
import asyncio
import os
import sys
sys.path.append(os.getcwd())
from database import get_db, db_execute

async def main():
    db = get_db()
    table_name = sys.argv[1] if len(sys.argv) > 1 else "expenditure_requests"
    try:
        # Get one record and check keys
        res = await db_execute(lambda: db.table(table_name).select("*").limit(1).execute())
        if res.data:
            print(f"Columns found in {table_name}:")
            for col in res.data[0].keys():
                print(f"- {col}")
        else:
            print(f"No data found in {table_name} to check columns.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

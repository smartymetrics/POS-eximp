import asyncio
from database import get_db, db_execute

async def check():
    db = get_db()
    try:
        res = await db_execute(lambda: db.table('admins').select('*').limit(1).execute())
        if res.data:
            print(f"Columns: {list(res.data[0].keys())}")
        else:
            print("No admin data found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())

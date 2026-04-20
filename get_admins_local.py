import asyncio
import os
import sys

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

async def main():
    try:
        from database import get_db, db_execute
        db = get_db()
        res = await db_execute(lambda: db.table("admins").select("id, full_name").eq("is_active", True).execute())
        if res.data:
            for admin in res.data:
                print(f"MATCH_RECORD|{admin['id']}|{admin['full_name']}")
        else:
            print("NO_ADMINS_FOUND")
    except Exception as e:
        print(f"ERROR_DURING_FETCH|{e}")

if __name__ == "__main__":
    asyncio.run(main())

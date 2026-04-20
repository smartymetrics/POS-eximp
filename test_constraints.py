import asyncio
import os
import sys

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from database import get_db, db_execute

async def main():
    try:
        from database import get_db, db_execute
        db = get_db()
        # PostgREST doesn't give schema directly, but we can try to find out by inserting a null email.
        print("Testing email nullability...")
        res = await db_execute(lambda: db.table("clients").insert({
            "full_name": "Test Null Email",
            "phone": "+2340000000000",
            "email": None
        }).execute())
        if res.data:
            print("SUCCESS: email column is NULLABLE")
            # Cleanup
            await db_execute(lambda: db.table("clients").delete().eq("id", res.data[0]["id"]).execute())
        else:
            print("FAILURE: email column is likely NOT NULL")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())

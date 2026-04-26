import asyncio
from database import get_db, db_execute

async def check_table():
    db = get_db()
    print("Checking if 'departments' table exists...")
    try:
        res = await db_execute(lambda: db.table("departments").select("*").limit(1).execute())
        print(f"✅ Success! Table exists. Rows found: {len(res.data)}")
        
        print("\nAttempting to insert test record...")
        try:
            ins = await db_execute(lambda: db.table("departments").insert({"name": "DIAGNOSTIC_TEST"}).execute())
            print(f"✅ Success! Inserted record: {ins.data}")
            
            print("\nAttempting to delete test record...")
            dept_id = ins.data[0]["id"]
            dele = await db_execute(lambda: db.table("departments").delete().eq("id", dept_id).execute())
            print(f"✅ Success! Deleted record.")
        except Exception as e:
            print(f"❌ Failed to insert/delete: {e}")
            
    except Exception as e:
        print(f"❌ Failed to access 'departments' table: {e}")
        print("\nThis usually means the table hasn't been created yet.")

if __name__ == "__main__":
    asyncio.run(check_table())

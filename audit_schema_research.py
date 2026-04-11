import asyncio
from database import get_db, db_execute

async def audit_schema():
    db = get_db()
    print("--- DB AUDIT: Checking for auth.users references ---")
    
    tables_to_check = ["properties", "documents", "campaigns", "marketing_events"]
    
    # Check table existence and columns
    for table in tables_to_check:
        try:
            res = await db_execute(lambda: db.table(table).select("*").limit(1).execute())
            print(f"✅ Table '{table}' EXISTS.")
        except Exception as e:
            if "not found" in str(e).lower() or "not exist" in str(e).lower():
                print(f"❌ Table '{table}' MISSING.")
            else:
                print(f"⚠️ Table '{table}' ERROR: {e}")

    # Check Columns for specific fields
    queries = [
        ("properties", "owner_agent_id"),
        ("documents", "created_by"),
        ("campaigns", "created_by"),
        ("marketing_events", "created_by")
    ]
    
    print("\n--- Field Check ---")
    for table, col in queries:
        try:
            res = await db_execute(lambda: db.table(table).select(col).limit(1).execute())
            print(f"✅ {table}.{col} EXISTS.")
        except Exception as e:
            print(f"❌ {table}.{col} MISSING or ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(audit_schema())

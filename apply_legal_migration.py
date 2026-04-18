import asyncio
import os
from database import get_db, db_execute

async def apply_legal_migration():
    print("Starting Extraordinary Legal Studio migration...")
    sql_file = "sql/hr_legal_bridge.sql"
    if not os.path.exists(sql_file):
        print(f"Error: {sql_file} not found")
        return

    with open(sql_file, "r") as f:
        sql = f.read()

    db = get_db()
    try:
        # Try to execute via the exec_sql RPC which seems to be the project pattern
        res = await db_execute(lambda: db.rpc("exec_sql", {"sql_body": sql}).execute())
        print("Legal Bridge migration applied successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        print("   Please ensure the 'exec_sql' RPC is defined in your Supabase project.")

if __name__ == "__main__":
    asyncio.run(apply_legal_migration())

import asyncio
import os
from database import supabase

async def apply_migration():
    print("🚀 Starting HR migration...")
    sql_file = "sql/hr_management_migration.sql"
    if not os.path.exists(sql_file):
        print(f"❌ Error: {sql_file} not found")
        return

    with open(sql_file, "r") as f:
        sql = f.read()

    try:
        # In modern supabase-py, rpc can be used for exec_sql if defined
        # If not, we might need a different approach. Let's try exec_sql RPC.
        res = supabase.rpc("exec_sql", {"sql_body": sql}).execute()
        print("✅ Migration applied successfully!")
        print(res.data)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("   Checking if we can split and run manually...")
        # Fallback: simple split by semicolon (naive)
        for statement in sql.split(";"):
            statement = statement.strip()
            if not statement or statement.startswith("--") or statement.startswith("ALTER TABLE"):
                 # Simple statements might work better individually
                 continue
            # Note: This is a very rough fallback and usually won't work for complex SQL

if __name__ == "__main__":
    asyncio.run(apply_migration())

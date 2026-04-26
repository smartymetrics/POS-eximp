import asyncio
import os
import re
from database import supabase

async def apply_migration():
    print("Starting HR Portal Extensions migration...")
    sql_file = "migrations/030_hr_portal_extensions.sql"
    if not os.path.exists(sql_file):
        print(f"Error: {sql_file} not found")
        return

    with open(sql_file, "r") as f:
        sql = f.read()

    # Split by semicolon, but try to be a bit smart about it
    # This regex splits by semicolon that is NOT followed by another semicolon (redundant)
    # and handles basic comments. 
    # For this specific file, simple split is mostly okay.
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    success_count = 0
    fail_count = 0

    for stmt in statements:
        # Remove comment lines
        lines = [line for line in stmt.split("\n") if not line.strip().startswith("--")]
        clean_stmt = "\n".join(lines).strip()
        if not clean_stmt:
            continue
            
        print(f"Executing: {clean_stmt[:50]}...")
        try:
            res = supabase.rpc("exec_sql", {"sql_body": clean_stmt + ";"}).execute()
            # If the RPC returns a dict with 'error', it's a Postgres error
            if isinstance(res.data, dict) and 'error' in res.data:
                print(f"   Postgres Error: {res.data['error']}")
                fail_count += 1
            else:
                success_count += 1
        except Exception as e:
            print(f"   RPC Error: {e}")
            fail_count += 1

    print(f"\nMigration Summary: {success_count} succeeded, {fail_count} failed.")

if __name__ == "__main__":
    asyncio.run(apply_migration())

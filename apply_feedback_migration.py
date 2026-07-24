import asyncio
import os
import sys
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import supabase, init_db

async def apply_migration():
    print("Starting Client Feedback migration (statement-by-statement)...")
    await init_db()
    
    sql_file = "sql/create_client_feedback_table.sql"
    if not os.path.exists(sql_file):
        print(f"Error: {sql_file} not found")
        return

    with open(sql_file, "r") as f:
        sql_content = f.read()

    # Split statements by semicolon, ignoring comments
    # Remove single-line comments
    sql_clean = re.sub(r'--.*?\n', '\n', sql_content)
    
    # Split by semicolon
    statements = sql_clean.split(";")
    
    success_count = 0
    fail_count = 0

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
            
        print(f"Executing SQL Statement: {stmt[:60]}...")
        try:
            res = supabase.rpc("exec_sql", {"sql_body": stmt}).execute()
            if isinstance(res.data, dict) and 'error' in res.data:
                print(f"  Result error: {res.data['error']}")
                fail_count += 1
            else:
                print("  Result: Success")
                success_count += 1
        except Exception as e:
            print(f"  Failed: {e}")
            fail_count += 1

    print(f"\nMigration completed: {success_count} statements succeeded, {fail_count} failed.")

if __name__ == "__main__":
    asyncio.run(apply_migration())

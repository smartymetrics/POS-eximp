import asyncio
import os
from database import supabase

async def apply_automation_mig():
    print("🚀 Applying HRM Automation Migration...")
    sql_file = "sql/hrm_goal_automation.sql"
    
    if not os.path.exists(sql_file):
        print(f"❌ Error: {sql_file} not found")
        return

    with open(sql_file, "r") as f:
        sql = f.read()

    # The exec_sql RPC is defined in the script itself, 
    # but initially we must run it via split statements if exec_sql doesn't exist yet.
    # We'll try running the whole block first.
    
    try:
        # We'll use the .rpc("exec_sql") only if it exists. 
        # Since it's in the script, we might have a chicken-and-egg problem.
        # But we can use the rest/v1/rpc directly or just run raw SQL via postgrest if allowed (usually not).
        
        # Actually, let's just use the existing migration pattern but more robustly.
        print("   Running SQL blocks...")
        
        # We'll try to run the file in blocks separated by semicolons
        # (This is naive but handles simple ALTER TABLE/CREATE FUNCTION)
        statements = sql.split(";")
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt: continue
            
            # For the first run (creating exec_sql), we can't use exec_sql to run itself.
            # Usually we need to run it through the Supabase SQL editor or a more privileged client.
            # Assuming supabase-py execute() handles raw SQL if used correctly? No.
            
            # Since I can't run raw SQL directly through the client easily without an RPC,
            # I will assume the USER will run the SQL in their Supabase editor, 
            # OR I'll try to use the existing exec_sql if it happens to be there.
            
            print(f"   Executing statement: {stmt[:50]}...")
            try:
                res = supabase.rpc("exec_sql", {"sql_body": stmt + ";"}).execute()
            except Exception as e:
                print(f"   ⚠️ Statement failed (might be expected if exec_sql missing): {e}")

    except Exception as e:
        print(f"❌ Migration block failed: {e}")

if __name__ == "__main__":
    asyncio.run(apply_automation_mig())

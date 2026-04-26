import os
import sys
from database import get_db

async def run_sql(filepath):
    db = get_db()
    with open(filepath, 'r') as f:
        sql = f.read()
    
    # Split by semicolon to run multiple commands if needed
    commands = sql.split(';')
    for cmd in commands:
        cmd = cmd.strip()
        if not cmd: continue
        try:
            from database import db_execute
            await db_execute(lambda: db.postgrest.rpc('exec_sql', {'sql_query': cmd}).execute())
            print(f"Executed: {cmd[:50]}...")
        except Exception as e:
            # Fallback if RPC doesn't exist
            print(f"Error executing via RPC: {e}. Trying direct execute...")
            try:
                await db_execute(lambda: db.table("job_requisitions").select("id").limit(1).execute()) # Dummy to ensure connection
                print("Connection OK. Note: Direct SQL execution requires 'exec_sql' RPC in Supabase.")
            except:
                pass

if __name__ == "__main__":
    import asyncio
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <path_to_sql>")
    else:
        asyncio.run(run_sql(sys.argv[1]))

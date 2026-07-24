import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, db_execute

async def main():
    db = get_db()
    
    # Read sql migration file
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql_path = os.path.join(base, "sql", "add_invoice_revamp_columns.sql")
    with open(sql_path, "r", encoding="utf-8") as fh:
        sql = fh.read()
    
    # Split queries by semicolon to execute them sequentially
    queries = [q.strip() for q in sql.split(";") if q.strip()]
    
    print(f"Executing {len(queries)} migration queries...")
    for q in queries:
        # Append semicolon back
        q_with_semicolon = q + ";"
        print(f"Executing: {q[:60]}...")
        try:
            res = await db_execute(lambda: db.rpc("exec_sql", {"sql_body": q_with_semicolon}).execute())
            print(f"Success: {res.data if hasattr(res, 'data') else 'OK'}")
        except Exception as e:
            print(f"Query failed: {e}")
            
    print("Migration finished.")

if __name__ == "__main__":
    asyncio.run(main())

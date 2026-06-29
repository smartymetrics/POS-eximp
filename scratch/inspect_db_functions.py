import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, db_execute

async def main():
    db = get_db()
    
    # Query parameters for exec_sql
    sql = "SELECT parameter_name, data_type, parameter_mode FROM information_schema.parameters WHERE specific_name IN (SELECT specific_name FROM information_schema.routines WHERE routine_name = 'exec_sql')"
    try:
        res = await db_execute(lambda: db.rpc("exec_sql", {"sql_body": sql}).execute())
        print(f"Parameters of exec_sql: {res.data}")
    except Exception as e:
        print(f"Failed parameters check: {e}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from database import get_db, db_execute

async def migrate():
    db = get_db()
    sql = "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS is_remote BOOLEAN DEFAULT FALSE;"
    print(f"Running SQL: {sql}")
    res = await db_execute(lambda: db.rpc("exec_sql", {"sql_body": sql}).execute())
    print(f"Result: {res.data}")

if __name__ == "__main__":
    asyncio.run(migrate())

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, db_execute

async def main():
    db = get_db()
    res = await db_execute(lambda: db.table('legal_matters').select('*').eq('id', '65c8bc73-2036-4fe7-b670-d54e75fc9de0').execute())
    if res.data:
        matter = res.data[0]
        print(f"Matter found!")
        print(f"ID: {matter['id']}")
        print(f"staff_id: {matter['staff_id']}")
        print(f"staff_visible: {matter['staff_visible']}")
    else:
        print("Matter NOT FOUND in DB.")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, db_execute

async def check_properties():
    db = get_db()
    res = await db_execute(lambda: db.table("properties").select("name, available_plot_sizes, starting_price, description").limit(5).execute())
    if res.data:
        for p in res.data:
            print(f"Name: {p.get('name')}")
            print(f"Available Sizes: {p.get('available_plot_sizes')}")
            print(f"Starting Price: {p.get('starting_price')}")
            print(f"Description: {p.get('description')}")
            print("-" * 20)
    else:
        print("No properties found.")

if __name__ == "__main__":
    asyncio.run(check_properties())

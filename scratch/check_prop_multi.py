import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, db_execute

async def check_properties_multi():
    db = get_db()
    res = await db_execute(lambda: db.table("properties").select("name, plot_size_sqm, starting_price, price_per_sqm").execute())
    if res.data:
        # Group by name
        estates = {}
        for p in res.data:
            name = p.get('name')
            if name not in estates: estates[name] = []
            estates[name].append(p)
        
        for name, variations in estates.items():
            print(f"Estate: {name}")
            for v in variations:
                print(f"  - Size: {v.get('plot_size_sqm')} SQM | Price: {v.get('starting_price') or v.get('price_per_sqm')}")
            print("-" * 20)
    else:
        print("No properties found.")

if __name__ == "__main__":
    asyncio.run(check_properties_multi())

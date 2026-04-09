import database, json
from routers.marketing_analytics import get_marketing_overview
import asyncio

async def main():
    db = database.get_db()
    data = await get_marketing_overview(current_admin={"id":"1"})
    print(f"Total Spend Computed: {data['campaigns']['total_spend']}")

if __name__ == "__main__":
    asyncio.run(main())

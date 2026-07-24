import asyncio
import os
from database import get_db, db_execute

async def main():
    db = get_db()
    res = await db_execute(lambda: db.table("invoices").select("*").eq("invoice_number", "EC-000090").execute())
    if res.data:
        print("INVOICE RECORD:")
        for k, v in res.data[0].items():
            print(f"  {k}: {v}")
    else:
        print("INVOICE NOT FOUND")

    sub_res = await db_execute(lambda: db.table("property_subscriptions").select("*").eq("id", res.data[0]["id"] if res.data else "").execute())
    if sub_res.data:
        print("\nPROPERTY SUBSCRIPTION RECORD:")
        for k, v in sub_res.data[0].items():
            print(f"  {k}: {v}")
    else:
        # Search by client id
        if res.data:
            c_id = res.data[0]["client_id"]
            sub_res2 = await db_execute(lambda: db.table("property_subscriptions").select("*").eq("client_id", c_id).execute())
            if sub_res2.data:
                print("\nPROPERTY SUBSCRIPTION RECORD (by client_id):")
                for k, v in sub_res2.data[0].items():
                    print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())


import os
import sys

# Add the current directory to sys.path so we can import database
sys.path.append(os.getcwd())

from database import get_db, db_execute
import asyncio

async def main():
    db = get_db()
    invoice_number = "EC-000020"
    res = await db_execute(lambda: db.table("invoices").select("*").eq("invoice_number", invoice_number).execute())
    if res.data:
        inv = res.data[0]
        print(f"INVOICE {invoice_number} DATA:")
        for k, v in inv.items():
            print(f"  {k}: {v}")
            
        # specifically check pipeline_stage
        stage = inv.get("pipeline_stage")
        print(f"\nCURRENT PIPELINE STAGE: '{stage}'")
    else:
        print(f"INVOICE {invoice_number} NOT FOUND")

if __name__ == "__main__":
    asyncio.run(main())

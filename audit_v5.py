import asyncio
import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def audit_v5():
    db = get_db()
    email = "Oscarmaxwell05@gmail.com"
    
    # 1. CLIENT
    c = db.table("clients").select("id").eq("email", email).execute()
    cid = c.data[0]["id"]
    
    # 2. INVOICE Number
    inv_num = db.rpc("generate_invoice_number").execute().data
    print(f"New Inv Num: {inv_num}")
    
    # 3. INSERT
    i_res = db.table("invoices").insert({
        "invoice_number": inv_num,
        "client_id": cid,
        "property_name": "Audit Test",
        "amount": 1234,
        "source": "manual"
    }).execute()
    iid = i_res.data[0]["id"]
    print(f"Inserted ID: {iid}")
    
    # 4. IMMEDIATELY SELECT BACK
    verify = db.table("invoices").select("*").eq("id", iid).execute()
    print(f"Verification Select: {verify.data}")

if __name__ == "__main__":
    asyncio.run(audit_v5())

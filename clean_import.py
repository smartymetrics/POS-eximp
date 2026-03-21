import asyncio
import os
import re
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def clean_import():
    db = get_db()
    
    # 1. CLEAN CLIENT
    email = "Oscarmaxwell05@gmail.com"
    print(f"Working on {email}...")
    
    # Try to find
    res = db.table("clients").select("id").eq("email", email).execute()
    if res.data:
        cid = res.data[0]["id"]
        print(f"Found client {cid}")
    else:
        print("Creating client...")
        res = db.table("clients").insert({"full_name": "Maxwell Osakwe", "email": email}).execute()
        cid = res.data[0]["id"]
        print(f"Created client {cid}")
        
    # 2. INVOICE
    # Get invoice number
    try:
        inv_num = db.rpc("generate_invoice_number").execute().data
        print(f"Generated Inv: {inv_num}")
    except:
        inv_num = "IMP-0001"
        print(f"Manual Inv: {inv_num}")
        
    invoice_data = {
        "invoice_number": inv_num,
        "client_id": cid,
        "amount": 0,
        "due_date": "2025-12-18",
        "property_name": "Prime Circle Estate"
    }
    
    print("Inserting invoice...")
    try:
        res = db.table("invoices").insert(invoice_data).execute()
        print(f" ✅ Invoice Success: {res.data[0]['id']}")
    except Exception as e:
        print(f" ❌ Invoice Fail: {e}")

if __name__ == "__main__":
    asyncio.run(clean_import())

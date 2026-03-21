import asyncio
import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def reproduce_maxwell_fail():
    db = get_db()
    email = "Oscarmaxwell05@gmail.com"
    client_res = db.table("clients").select("id").eq("email", email).execute()
    if not client_res.data:
        print(f"Creating client {email}...")
        client_res = db.table("clients").insert({"full_name": "Maxwell Osakwe", "email": email}).execute()
    
    cid = client_res.data[0]["id"]
    
    invoice_number = db.rpc("generate_invoice_number").execute().data
    print(f"Testing with Invoice: {invoice_number}")
    
    # Maxwell's exact data
    invoice_insert = {
        "invoice_number": invoice_number,
        "client_id": cid,
        "property_name": "Prime Circle Estate",
        "plot_size_sqm": 500.0,
        "amount": 0.0,
        "amount_paid": 0.0,
        "payment_terms": "Outright",
        "invoice_date": "2025-12-18",
        "due_date": "2025-12-18",
        "sales_rep_name": None,
        "co_owner_name": "Osakwe Maxwell Uche",
        "co_owner_email": "Ogwashi-uku, Delta state.",
        "signature_url": "https://drive.google.com/open?id=1MJ0LVcN3NL5yr-bf6bXGDDUl7964Ye55",
        "payment_proof_url": None,
        "passport_photo_url": "https://drive.google.com/open?id=1835U80hGrq5nzPOil6JY42K1MERxwPg0",
        "source": "spreadsheet_import"
    }
    
    try:
        res = db.table("invoices").insert(invoice_insert).execute()
        print(f" ✅ Success: {res.data}")
    except Exception as e:
        print(f" ❌ FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce_maxwell_fail())

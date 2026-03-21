import asyncio
import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def fix_migration():
    db = get_db()
    
    # 1. FIND DAMILOLA
    email = "oluwadamilolaadigun2580@gmail.com"
    client = db.table("clients").select("id").eq("email", email).execute().data[0]
    cid = client["id"]
    
    # 2. FIND/CREATE INVOICE
    inv_res = db.table("invoices").select("id").eq("client_id", cid).eq("invoice_number", "EC-000007").execute()
    if not inv_res.data:
        # Create it robustly
        print("Creating invoice for Damilola...")
        inv_res = db.table("invoices").insert({
            "invoice_number": "EC-000007",
            "client_id": cid,
            "property_name": "Eid/Easter Special landsale",
            "amount": 650000,
            "amount_paid": 200000,
            "payment_terms": "Installment",
            "invoice_date": "2026-03-18",
            "due_date": "2026-03-18",
            "source": "manual"
        }).execute()
    
    iid = inv_res.data[0]["id"]
    print(f"Invoice ID: {iid}")
    
    # 3. PAYMENT
    print("Inserting payment for Damilola...")
    try:
        db.table("payments").insert({
            "invoice_id": iid,
            "client_id": cid,
            "amount": 200000,
            "payment_method": "Bank Transfer",
            "payment_date": "2026-03-18",
            "reference": "2026-03-18_import",
            "notes": "Imported from spreadsheet"
        }).execute()
        print(" ✅ Payment success")
    except Exception as e:
        print(f" ❌ Payment fail: {e}")
        
    # 4. VERIFICATION
    print("Inserting verification for Damilola...")
    try:
        db.table("pending_verifications").insert({
            "invoice_id": iid,
            "client_id": cid,
            "payment_proof_url": "https://drive.google.com/open?id=1D7kFv_IEZN2EHxIc-yfhG37Lw0bZs_0E",
            "deposit_amount": 200000,
            "payment_date": "2026-03-18",
            "status": "pending"
        }).execute()
        print(" ✅ Verification success")
    except Exception as e:
        print(f" ❌ Verification fail: {e}")

if __name__ == "__main__":
    asyncio.run(fix_migration())

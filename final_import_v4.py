import asyncio
import os
import re
from database import get_db
from dotenv import load_dotenv

load_dotenv()

DATA = [
    {
        "email": "Oscarmaxwell05@gmail.com",
        "first_name": "Maxwell",
        "last_name": "Osakwe",
        "middle_name": "Uche",
        "title": "Mr.",
        "gender": "Male",
        "dob": "2000-02-05",
        "address": "Ogwashi-uku, Delta state.",
        "phone": "+258864231961",
        "occupation": "Business man",
        "marital_status": "Single",
        "nin": "74424328526",
        "id_number": "A12087121",
        "nationality": "Nigerian",
        "property_name": "Prime Circle Estate",
        "plot_size": "500 SQM",
        "nok_name": "Osakwe David Chidi",
        "nok_phone": "+234 808 679 7438",
        "signature": "https://drive.google.com/open?id=1MJ0LVcN3NL5yr-bf6bXGDDUl7964Ye55",
        "photo": "https://drive.google.com/open?id=1835U80hGrq5nzPOil6JY42K1MERxwPg0",
        "deposit": 0,
        "total": 0,
        "terms": "Outright",
        "date": "2025-12-18"
    },
    {
        "email": "doncharles376@gmail.com",
        "first_name": "Charles",
        "last_name": "Mbaogu",
        "middle_name": "Chiakpaoke",
        "title": "Master",
        "gender": "Male",
        "dob": "2002-03-09",
        "address": "Block 33K Lekki Pride 1.0 Estate Lekki Ajah Lagos State",
        "phone": "07066944984",
        "occupation": "Software Engineer",
        "marital_status": "Single",
        "nin": "10515573269",
        "nationality": "Nigerian",
        "property_name": "Coinfield Estate",
        "plot_size": "1000 SQM",
        "nok_name": "Mbaogu Martins Ewezugachi",
        "nok_phone": "+2348165288460",
        "signature": "https://drive.google.com/open?id=1pys3NdNzvKk9L9HnBEtAueFoEbQz2SwL",
        "photo": "https://drive.google.com/open?id=1YowKAUzc5W216GfsAuecyFIpILRCuR2p",
        "deposit": 0,
        "total": 0,
        "terms": "Outright",
        "date": "2025-12-29"
    },
    {
        "email": "mbaogudona@gmail.com",
        "first_name": "Donatus",
        "last_name": "Mbaogu",
        "middle_name": "Okechukwu",
        "title": "Mr.",
        "gender": "Male",
        "dob": "1957-06-04",
        "address": "No 3 Chief Boniface Avenue Izuoma Asa, Oyigbo Rivers State",
        "phone": "08035083789",
        "occupation": "Engineer",
        "marital_status": "Married",
        "nin": "40507294211",
        "nationality": "Nigerian",
        "property_name": "Coinfield Estate",
        "plot_size": "500 SQM",
        "nok_name": "Mbaogu Donatus Mgboatuchi",
        "nok_phone": "08132252759",
        "signature": "https://drive.google.com/open?id=1Mn8lxYhsY1jiUUuewOobPlGxjlAL1YX_",
        "photo": "https://drive.google.com/open?id=1tHxGTTSB0XUJ_xcSdM91e8B1w4_tMDUX",
        "deposit": 0,
        "total": 0,
        "terms": "Outright",
        "date": "2025-12-31"
    },
    {
        "email": "oluwadamilolaadigun2580@gmail.com",
        "first_name": "Damilola",
        "last_name": "Adigun",
        "middle_name": "David",
        "title": "Mr.",
        "gender": "Male",
        "dob": "1998-06-10",
        "address": "12 Dele Oladipo Street Moniya, Ibadan.",
        "phone": "09153031939",
        "occupation": "Consultant",
        "marital_status": "Single",
        "nin": "45656298654",
        "nationality": "Nigerian",
        "property_name": "Eid/Easter Special landsale",
        "plot_size": "300 SQM",
        "nok_name": "Kehinde Peter Damilare",
        "nok_phone": "07033221004",
        "signature": "https://drive.google.com/open?id=1Sei-tHgFFWRwe44_pOK2CINOWKey8zRR",
        "photo": "https://drive.google.com/open?id=112q_AcSCY5Sd_GZR4Wl3aXajEH65T78r",
        "deposit": 200000,
        "total": 650000,
        "terms": "Installment",
        "date": "2026-03-18",
        "pay_proof": "https://drive.google.com/open?id=1D7kFv_IEZN2EHxIc-yfhG37Lw0bZs_0E"
    }
]

async def final_import():
    db = get_db()
    
    # 0. REFRESH CHECK
    print("Checking unmatched_reps schema...")
    try:
        db.table("unmatched_reps").select("id").limit(1).execute()
        print(" ✅ unmatched_reps is visible")
    except Exception as e:
        print(f" ⚠️ unmatched_reps not visible: {e}")

    for row in DATA:
        print(f"Processing {row['first_name']}...")
        
        # 1. CLIENT
        full_name = f"{row['first_name']} {row['middle_name'] + ' ' if row['middle_name'] else ''}{row['last_name']}".strip()
        client_data = {
            "full_name": full_name,
            "email": row["email"],
            "phone": row["phone"],
            "address": row["address"],
            "title": row["title"],
            "middle_name": row["middle_name"],
            "gender": row["gender"],
            "dob": row["dob"],
            "marital_status": row["marital_status"],
            "occupation": row["occupation"],
            "nin": row["nin"],
            "nationality": row["nationality"],
            "passport_photo_url": row["photo"]
        }
        
        c = db.table("clients").select("id").eq("email", row["email"]).execute()
        if c.data: cid = c.data[0]["id"]; db.table("clients").update(client_data).eq("id", cid).execute()
        else: cid = db.table("clients").insert(client_data).execute().data[0]["id"]
        
        # 2. INVOICE Number
        inv_num = db.rpc("generate_invoice_number").execute().data
        
        # 3. INVOICE Insert (Direct, skipping sales_rep_name to avoid triggers)
        invoice_insert = {
            "invoice_number": inv_num,
            "client_id": cid,
            "property_name": row["property_name"],
            "amount": row["total"],
            "amount_paid": row["deposit"],
            "payment_terms": row["terms"],
            "invoice_date": row["date"],
            "due_date": row["date"],
            "source": "manual" # THIS SHOULD BYPASS WEBHOOK TRIGGERS
        }
        
        try:
            i_res = db.table("invoices").insert(invoice_insert).execute()
            iid = i_res.data[0]["id"]
            print(f" ✅ Invoice {inv_num} Created")
            
            # 4. PAYMENT
            if row["deposit"] > 0:
                db.table("payments").insert({
                    "invoice_id": iid,
                    "client_id": cid,
                    "amount": row["deposit"],
                    "payment_method": "Bank Transfer",
                    "payment_date": row["date"],
                    "reference": f"{row['date']}_imp"
                }).execute()
                print(" ✅ Payment Created")
                
            # 5. VERIFICATION
            if row.get("pay_proof"):
                db.table("pending_verifications").insert({
                    "invoice_id": iid,
                    "client_id": cid,
                    "payment_proof_url": row["pay_proof"],
                    "deposit_amount": row["deposit"],
                    "payment_date": row["date"]
                }).execute()
                print(" ✅ Verification Created")
                
        except Exception as e:
            print(f" ❌ ERROR for {row['first_name']}: {e}")

if __name__ == "__main__":
    asyncio.run(final_import())

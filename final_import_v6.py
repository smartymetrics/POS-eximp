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

async def final_import_v6():
    db = get_db()
    
    for row in DATA:
        print(f"Working on {row['first_name']}...")
        
        # 1. CLIENT
        full_name = f"{row['first_name']} {row['middle_name'] + ' ' if row['middle_name'] else ''}{row['last_name']}".strip()
        c = db.table("clients").select("id").eq("email", row["email"]).execute()
        if c.data: cid = c.data[0]["id"]
        else: cid = db.table("clients").insert({"full_name": full_name, "email": row["email"]}).execute().data[0]["id"]
        
        # 2. INVOICE Number
        inv_num = db.rpc("generate_invoice_number").execute().data
        
        # 3. INVOICE Insert
        try:
            i_res = db.table("invoices").insert({
                "invoice_number": inv_num,
                "client_id": cid,
                "property_name": row["property_name"],
                "amount": row["total"],
                "amount_paid": row["deposit"],
                "payment_terms": row["terms"],
                "invoice_date": row["date"],
                "due_date": row["date"],
                "source": "manual"
            }).execute()
            if i_res.data:
                iid = i_res.data[0]["id"]
                print(f" ✅ Created {inv_num} (ID: {iid})")
            else:
                print(f" ❌ FAILED to return data for {inv_num}")
        except Exception as e:
            print(f" ❌ ERROR for {row['first_name']}: {e}")

    # FINAL CHECK
    print("\nFINAL AUDIT IN SAME SESSION:")
    all_invs = db.table("invoices").select("invoice_number, clients(full_name)").execute()
    print(f"Total Invoices: {len(all_invs.data)}")
    for i in all_invs.data:
        print(f" - {i['invoice_number']} for {i['clients']['full_name']}")

if __name__ == "__main__":
    asyncio.run(final_import_v6())

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
        "nok_email": "Davidchidi508@gmail.com",
        "nok_occupation": "Student",
        "nok_relationship": "Sibling",
        "nok_address": "Ogwashi-uku, Delta state.",
        "signature_url": "https://drive.google.com/open?id=1MJ0LVcN3NL5yr-bf6bXGDDUl7964Ye55",
        "passport_photo": "https://drive.google.com/open?id=1835U80hGrq5nzPOil6JY42K1MERxwPg0",
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
        "nok_relationship": "Sibling",
        "nok_address": "No 3 Chief Boniface Avenue Izuoma Asa New Layout, Oyigbo Rivers State",
        "signature_url": "https://drive.google.com/open?id=1pys3NdNzvKk9L9HnBEtAueFoEbQz2SwL",
        "passport_photo": "https://drive.google.com/open?id=1YowKAUzc5W216GfsAuecyFIpILRCuR2p",
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
        "nok_email": "atuchimbaogu@gmail.com",
        "nok_relationship": "Child",
        "nok_address": "Plot 10 WTC Estate Enugu",
        "signature_url": "https://drive.google.com/open?id=1Mn8lxYhsY1jiUUuewOobPlGxjlAL1YX_",
        "passport_photo": "https://drive.google.com/open?id=1tHxGTTSB0XUJ_xcSdM91e8B1w4_tMDUX",
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
        "nok_email": "e032312.kehinde@dlc.ui.edu.ng",
        "nok_relationship": "Sibling",
        "nok_address": "No 12 dele Oladipo street, agotapa Moniya Ibadan",
        "signature_url": "https://drive.google.com/open?id=1Sei-tHgFFWRwe44_pOK2CINOWKey8zRR",
        "passport_photo": "https://drive.google.com/open?id=112q_AcSCY5Sd_GZR4Wl3aXajEH65T78r",
        "deposit": 200000,
        "total": 650000,
        "terms": "Installment",
        "date": "2026-03-18",
        "pay_proof": "https://drive.google.com/open?id=1D7kFv_IEZN2EHxIc-yfhG37Lw0bZs_0E"
    }
]

async def final_import():
    db = get_db()
    
    for row in DATA:
        print(f"Importing {row['first_name']}...")
        
        # 1. CLIENT (Upsert)
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
            "passport_photo_url": row["passport_photo"],
            "nok_name": row["nok_name"],
            "nok_phone": row["nok_phone"],
            "nok_email": row.get("nok_email"),
            "nok_address": row["nok_address"],
            "nok_relationship": row["nok_relationship"]
        }
        
        c_res = db.table("clients").select("id").eq("email", row["email"]).execute()
        if c_res.data:
            client_id = c_res.data[0]["id"]
            db.table("clients").update(client_data).eq("id", client_id).execute()
        else:
            c_res = db.table("clients").insert(client_data).execute()
            client_id = c_res.data[0]["id"]

        # 2. INVOICE (New)
        inv_num = db.rpc("generate_invoice_number").execute().data
        
        cleaned_size = re.sub(r'[^\d.]+', '', row["plot_size"])
        plot_size_numeric = float(cleaned_size) if cleaned_size else None
        
        invoice_insert = {
            "invoice_number": inv_num,
            "client_id": client_id,
            "property_name": row["property_name"],
            "plot_size_sqm": plot_size_numeric,
            "amount": row["total"],
            "amount_paid": row["deposit"],
            "payment_terms": row["terms"],
            "invoice_date": row["date"],
            "due_date": row["date"],
            "signature_url": row["signature_url"],
            "passport_photo_url": row["passport_photo"],
            "source": "manual"
        }
        
        i_res = db.table("invoices").insert(invoice_insert).execute()
        iid = i_res.data[0]["id"]
        
        # 3. PAYMENT
        if row["deposit"] > 0:
            db.table("payments").insert({
                "invoice_id": iid,
                "client_id": client_id,
                "amount": row["deposit"],
                "payment_method": "Bank Transfer",
                "payment_date": row["date"],
                "reference": f"{row['date']}_imp",
                "notes": "Spreadsheet Import"
            }).execute()
            
        # 4. VERIFICATION
        if row.get("pay_proof"):
            db.table("pending_verifications").insert({
                "invoice_id": iid,
                "client_id": client_id,
                "payment_proof_url": row["pay_proof"],
                "deposit_amount": row["deposit"],
                "payment_date": row["date"],
                "status": "pending"
            }).execute()
            
        print(f" ✅ Processed {row['first_name']} (Inv: {inv_num})")

if __name__ == "__main__":
    asyncio.run(final_import())

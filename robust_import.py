import asyncio
import os
import re
from datetime import datetime, date
from database import get_db
from dotenv import load_dotenv

load_dotenv()

DATA = [
    {
        "timestamp": "2025-12-18",
        "email": "Oscarmaxwell05@gmail.com",
        "passport_photo_url": "https://drive.google.com/open?id=1835U80hGrq5nzPOil6JY42K1MERxwPg0",
        "title": "Mr.",
        "first_name": "Maxwell",
        "last_name": "Osakwe",
        "middle_name": "Uche",
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
        "nok_name": "Osakwe David Chidi",
        "nok_phone": "+234 808 679 7438",
        "nok_email": "Davidchidi508@gmail.com",
        "nok_occupation": "Student",
        "nok_relationship": "Sibling",
        "nok_address": "Ogwashi-uku, Delta state.",
        "ownership_type": "Sole Owner",
        "co_owner_name": "Osakwe Maxwell Uche",
        "co_owner_email": "Ogwashi-uku, Delta state.",
        "signature_url": "https://drive.google.com/open?id=1MJ0LVcN3NL5yr-bf6bXGDDUl7964Ye55",
        "plot_size": "500 SQM",
        "payment_duration": "6 months",
        "deposit_amount": 0.0,
        "total_amount": 0.0,
        "payment_date": None,
        "payment_proof_url": None,
        "payment_terms": "Outright",
        "source_of_income": "Business Income",
        "referral_source": "Referral"
    },
    {
        "timestamp": "2025-12-29",
        "email": "doncharles376@gmail.com",
        "passport_photo_url": "https://drive.google.com/open?id=1YowKAUzc5W216GfsAuecyFIpILRCuR2p",
        "title": "Master",
        "first_name": "Charles",
        "last_name": "Mbaogu",
        "middle_name": "Chiakpaoke",
        "gender": "Male",
        "dob": "2002-03-09",
        "address": "Block 33K Lekki Pride 1.0 Estate Lekki Ajah Lagos State",
        "phone": "07066944984",
        "occupation": "Software Engineer",
        "marital_status": "Single",
        "nin": "10515573269",
        "id_number": None,
        "nationality": "Nigerian",
        "property_name": "Coinfield Estate",
        "nok_name": "Mbaogu Martins Ewezugachi",
        "nok_phone": "+2348165288460",
        "nok_email": None,
        "nok_occupation": "Student",
        "nok_relationship": "Sibling",
        "nok_address": "No 3 Chief Boniface Avenue Izuoma Asa New Layout, Oyigbo Rivers State",
        "ownership_type": "Sole Owner",
        "co_owner_name": "Charles Chiakpaoke Mbaogu",
        "co_owner_email": "doncharles376@gmail.com",
        "signature_url": "https://drive.google.com/open?id=1pys3NdNzvKk9L9HnBEtAueFoEbQz2SwL",
        "plot_size": "1000 SQM",
        "payment_duration": "6 months",
        "deposit_amount": 0.0,
        "total_amount": 0.0,
        "payment_date": None,
        "payment_proof_url": None,
        "payment_terms": "Outright",
        "source_of_income": "Business Income",
        "referral_source": "Salesperson"
    },
    {
        "timestamp": "2025-12-31",
        "email": "mbaogudona@gmail.com",
        "passport_photo_url": "https://drive.google.com/open?id=1tHxGTTSB0XUJ_xcSdM91e8B1w4_tMDUX",
        "title": "Mr.",
        "first_name": "Donatus",
        "last_name": "Mbaogu",
        "middle_name": "Okechukwu",
        "gender": "Male",
        "dob": "1957-06-04",
        "address": "No 3 Chief Boniface Avenue Izuoma Asa, Oyigbo Rivers State",
        "phone": "08035083789",
        "occupation": "Engineer",
        "marital_status": "Married",
        "nin": "40507294211",
        "id_number": None,
        "nationality": "Nigerian",
        "property_name": "Coinfield Estate",
        "nok_name": "Mbaogu Donatus Mgboatuchi",
        "nok_phone": "08132252759",
        "nok_email": "atuchimbaogu@gmail.com",
        "nok_occupation": "Mechanical Engineer",
        "nok_relationship": "Child",
        "nok_address": "Plot 10 WTC Estate Enugu",
        "ownership_type": "Sole Owner",
        "co_owner_name": "Donatus Okechukwu Mbaogu",
        "co_owner_email": "mbaogudona@gmail.com",
        "signature_url": "https://drive.google.com/open?id=1Mn8lxYhsY1jiUUuewOobPlGxjlAL1YX_",
        "plot_size": "500 SQM",
        "payment_duration": "6 months",
        "deposit_amount": 0.0,
        "total_amount": 0.0,
        "payment_date": None,
        "payment_proof_url": None,
        "payment_terms": "Outright",
        "source_of_income": "Personal Income",
        "referral_source": "Other"
    },
    {
        "timestamp": "2026-03-18",
        "email": "oluwadamilolaadigun2580@gmail.com",
        "passport_photo_url": "https://drive.google.com/open?id=112q_AcSCY5Sd_GZR4Wl3aXajEH65T78r",
        "title": "Mr.",
        "first_name": "Damilola",
        "last_name": "Adigun",
        "middle_name": "David",
        "gender": "Male",
        "dob": "1998-06-10",
        "address": "12 Dele Oladipo Street Moniya, Ibadan.",
        "phone": "09153031939",
        "occupation": "Consultant",
        "marital_status": "Single",
        "nin": "45656298654",
        "id_number": "45656298654",
        "id_document_url": "https://drive.google.com/open?id=14Ep2rvbSBtge_2KEcNT5d8dP81KxIwew",
        "nationality": "Nigerian",
        "property_name": "Eid/Easter Special landsale",
        "nok_name": "Kehinde Peter Damilare",
        "nok_phone": "07033221004",
        "nok_email": "e032312.kehinde@dlc.ui.edu.ng",
        "nok_occupation": "Librarian",
        "nok_relationship": "Sibling",
        "nok_address": "No 12 dele Oladipo street, agotapa Moniya Ibadan",
        "ownership_type": "Sole Owner",
        "co_owner_name": None,
        "co_owner_email": None,
        "signature_url": "https://drive.google.com/open?id=1Sei-tHgFFWRwe44_pOK2CINOWKey8zRR",
        "plot_size": "300 SQM",
        "payment_duration": "3 months",
        "deposit_amount": 200000.0,
        "total_amount": 650000.0,
        "payment_date": "2026-03-18",
        "payment_proof_url": "https://drive.google.com/open?id=1D7kFv_IEZN2EHxIc-yfhG37Lw0bZs_0E",
        "payment_terms": "Installment",
        "source_of_income": "Loan",
        "referral_source": "Referral"
    }
]

async def robust_import():
    db = get_db()
    
    # 0. CLEANUP OLD ATTEMPTS
    print("Cleaning up old import attempts...")
    db.table("invoices").delete().in_("invoice_number", ["EC-000002", "EC-000003", "EC-000004", "EC-000005", "EC-000006", "EC-000007"]).execute()
    
    for row in DATA:
        print(f"Importing {row['first_name']} {row['last_name']}...")
        
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
            "id_number": row.get("id_number"),
            "id_document_url": row.get("id_document_url"),
            "nationality": row["nationality"],
            "passport_photo_url": row["passport_photo_url"],
            "nok_name": row["nok_name"],
            "nok_phone": row["nok_phone"],
            "nok_email": row["nok_email"],
            "nok_occupation": row.get("nok_occupation"),
            "nok_relationship": row["nok_relationship"],
            "nok_address": row["nok_address"],
            "source_of_income": row["source_of_income"],
            "referral_source": row["referral_source"]
        }
        
        # Upsert
        c_res = db.table("clients").select("id").eq("email", row["email"]).execute()
        if c_res.data:
            client_id = c_res.data[0]["id"]
            db.table("clients").update(client_data).eq("id", client_id).execute()
        else:
            c_res = db.table("clients").insert(client_data).execute()
            client_id = c_res.data[0]["id"]
            
        # 2. INVOICE
        inv_num = db.rpc("generate_invoice_number").execute().data
        
        # Plot size numeric
        plot_size_numeric = None
        if row["plot_size"]:
            cleaned_size = re.sub(r'[^\d.]+', '', row["plot_size"])
            if cleaned_size: plot_size_numeric = float(cleaned_size)

        invoice_insert = {
            "invoice_number": inv_num,
            "client_id": client_id,
            "property_name": row["property_name"],
            "plot_size_sqm": plot_size_numeric,
            "amount": row["total_amount"],
            "amount_paid": row["deposit_amount"],
            "payment_terms": row["payment_terms"],
            "invoice_date": row["timestamp"],
            "due_date": row["timestamp"],
            "signature_url": row["signature_url"],
            "payment_proof_url": row["payment_proof_url"],
            "passport_photo_url": row["passport_photo_url"],
            "source": "manual" # Use manual to bypass some triggers if any
        }
        
        i_res = db.table("invoices").insert(invoice_insert).execute()
        invoice_id = i_res.data[0]["id"]
        
        # 3. PAYMENT
        if row["deposit_amount"] > 0:
            db.table("payments").insert({
                "invoice_id": invoice_id,
                "client_id": client_id,
                "reference": f"{row['timestamp']}_import",
                "amount": row["deposit_amount"],
                "payment_method": "Bank Transfer",
                "payment_date": row["timestamp"],
                "notes": "Imported from spreadsheet"
            }).execute()
        
        # 4. VERIFICATION
        if row["payment_proof_url"]:
            try:
                db.table("pending_verifications").insert({
                    "invoice_id": invoice_id,
                    "client_id": client_id,
                    "payment_proof_url": row["payment_proof_url"],
                    "deposit_amount": row["deposit_amount"],
                    "payment_date": row["timestamp"],
                    "status": "pending"
                }).execute()
            except Exception as e:
                print(f" ⚠️ Verification insert failed for {full_name}: {e}")

        print(f" ✅ Success for {full_name} (Inv: {inv_num})")

if __name__ == "__main__":
    asyncio.run(robust_import())

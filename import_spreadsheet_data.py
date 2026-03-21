import asyncio
import os
import re
from datetime import datetime
from database import get_db
from dotenv import load_dotenv

load_dotenv()

# The data provided by the user (parsed into a list of dicts)
DATA = [
    {
        "timestamp": "12/18/2025 15:58:33",
        "email": "Oscarmaxwell05@gmail.com",
        "passport_photo": "https://drive.google.com/open?id=1835U80hGrq5nzPOil6JY42K1MERxwPg0",
        "title": "Mr.",
        "first_name": "Maxwell",
        "last_name": "Osakwe",
        "middle_name": "Uche",
        "gender": "Male",
        "dob": "2/5/2000",
        "address": "Ogwashi-uku, Delta state.",
        "client_email": "Oscarmaxwell05@gmail.com",
        "marital": "Single",
        "phone": "+258864231961",
        "occupation": "Business man",
        "nin": "74424328526",
        "id_number": "A12087121",
        "id_doc": "",
        "nationality": "Nigerian",
        "property_name": "Prime Circle Estate",
        "nok_name": "Osakwe David Chidi",
        "nok_phone": "+234 808 679 7438",
        "nok_email": "Davidchidi508@gmail.com",
        "nok_occupation": "Student",
        "nok_relationship": "Sibling",
        "nok_address": "Ogwashi-uku, Delta state.",
        "ownership": "I am the sole owner of this property",
        "co_owner_name": "Osakwe Maxwell Uche",
        "co_owner_email": "Ogwashi-uku, Delta state.", # OOPS, looks like address was entered in email field?
        "signature": "https://drive.google.com/open?id=1MJ0LVcN3NL5yr-bf6bXGDDUl7964Ye55",
        "plot_size": "500 SQM",
        "duration": "6 months",
        "deposit": 0,
        "pay_date": "",
        "pay_proof": "",
        "outstanding": 0,
        "income": "Business Income",
        "referral": "Referral",
        "consent": "I Confirm and Agree",
        "rep_name": "",
        "rep_phone": ""
    },
    {
        "timestamp": "12/29/2025 7:00:57",
        "email": "doncharles376@gmail.com",
        "passport_photo": "https://drive.google.com/open?id=1YowKAUzc5W216GfsAuecyFIpILRCuR2p",
        "title": "Master",
        "first_name": "Charles",
        "last_name": "Mbaogu",
        "middle_name": "Chiakpaoke",
        "gender": "Male",
        "dob": "3/9/2002",
        "address": "Block 33K Lekki Pride 1.0 Estate Lekki Ajah Lagos State",
        "client_email": "doncharles376@gmail.com",
        "marital": "Single",
        "phone": "07066944984",
        "occupation": "Software Engineer",
        "nin": "10515573269",
        "id_number": "",
        "id_doc": "",
        "nationality": "Nigerian",
        "property_name": "Coinfield Estate",
        "nok_name": "Mbaogu Martins Ewezugachi",
        "nok_phone": "+2348165288460",
        "nok_email": "",
        "nok_occupation": "Student",
        "nok_relationship": "Sibling",
        "nok_address": "No 3 Chief Boniface Avenue Izuoma Asa New Layout, Oyigbo Rivers State",
        "ownership": "I am the sole owner of this property",
        "co_owner_name": "Mbaogu Charles Chiakpaoke",
        "co_owner_email": "doncharles376@gmail.com",
        "signature": "https://drive.google.com/open?id=1pys3NdNzvKk9L9HnBEtAueFoEbQz2SwL",
        "plot_size": "1000 SQM",
        "duration": "6 months",
        "deposit": 0,
        "pay_date": "",
        "pay_proof": "",
        "outstanding": 0,
        "income": "Business Income",
        "referral": "Salesperson",
        "consent": "I Confirm and Agree",
        "rep_name": "",
        "rep_phone": ""
    },
    {
        "timestamp": "12/31/2025 18:04:33",
        "email": "mbaogudona@gmail.com",
        "passport_photo": "https://drive.google.com/open?id=1tHxGTTSB0XUJ_xcSdM91e8B1w4_tMDUX",
        "title": "Mr.",
        "first_name": "Donatus",
        "last_name": "Mbaogu",
        "middle_name": "Okechukwu",
        "gender": "Male",
        "dob": "6/4/1957",
        "address": "No 3 Chief Boniface Avenue Izuoma Asa, Oyigbo Rivers State",
        "client_email": "mbaogudona@gmail.com",
        "marital": "Married",
        "phone": "08035083789",
        "occupation": "Engineer",
        "nin": "40507294211",
        "id_number": "",
        "id_doc": "",
        "nationality": "Nigerian",
        "property_name": "Coinfield Estate",
        "nok_name": "Mbaogu Donatus Mgboatuchi",
        "nok_phone": "08132252759",
        "nok_email": "atuchimbaogu@gmail.com",
        "nok_occupation": "Mechanical Engineer",
        "nok_relationship": "Child",
        "nok_address": "Plot 10 WTC Estate Enugu",
        "ownership": "I am the sole owner of this property",
        "co_owner_name": "Mbaogu Donatus Okechukwu",
        "co_owner_email": "mbaogudona@gmail.com",
        "signature": "https://drive.google.com/open?id=1Mn8lxYhsY1jiUUuewOobPlGxjlAL1YX_",
        "plot_size": "500 SQM",
        "duration": "6 months",
        "deposit": 0,
        "pay_date": "",
        "pay_proof": "",
        "outstanding": 0,
        "income": "Personal Income",
        "referral": "Other",
        "consent": "I Confirm and Agree",
        "rep_name": "",
        "rep_phone": ""
    },
    {
        "timestamp": "3/18/2026 17:37:10",
        "email": "oluwadamilolaadigun2580@gmail.com",
        "passport_photo": "https://drive.google.com/open?id=112q_AcSCY5Sd_GZR4Wl3aXajEH65T78r",
        "title": "Mr.",
        "first_name": "Damilola",
        "last_name": "Adigun",
        "middle_name": "David",
        "gender": "Male",
        "dob": "6/10/1998",
        "address": "12 Dele Oladipo Street Moniya, Ibadan.",
        "client_email": "oluwadamilolaadigun2580@gmail.com",
        "marital": "Single",
        "phone": "09153031939",
        "occupation": "Consultant",
        "nin": "45656298654",
        "id_number": "45656298654",
        "id_doc": "https://drive.google.com/open?id=14Ep2rvbSBtge_2KEcNT5d8dP81KxIwew",
        "nationality": "Nigerian",
        "property_name": "Eid/Easter Special landsale 300sqm with 200k deposit.",
        "nok_name": "Kehinde Peter Damilare",
        "nok_phone": "07033221004",
        "nok_email": "e032312.kehinde@dlc.ui.edu.ng",
        "nok_occupation": "Librarian",
        "nok_relationship": "Sibling",
        "nok_address": "No 12 dele Oladipo street, agotapa Moniya Ibadan",
        "ownership": "I am the sole owner of this property",
        "co_owner_name": "No name",
        "co_owner_email": "No email",
        "signature": "https://drive.google.com/open?id=1Sei-tHgFFWRwe44_pOK2CINOWKey8zRR",
        "plot_size": "300 SQM",
        "duration": "3 months",
        "deposit": 200000,
        "pay_date": "3/18/2026",
        "pay_proof": "https://drive.google.com/open?id=1D7kFv_IEZN2EHxIc-yfhG37Lw0bZs_0E",
        "outstanding": 450000,
        "income": "Loan",
        "referral": "Referral",
        "consent": "I Confirm and Agree",
        "rep_name": "",
        "rep_phone": ""
    }
]

def clean_amount(val):
    if isinstance(val, (int, float)): return float(val)
    if not val or val == "N/A": return 0.0
    return float(re.sub(r'[^\d.]+', '', str(val)))

def parse_date(date_str):
    if not date_str: return str(datetime.now().date())
    try:
        # Try M/D/YYYY
        return datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
    except:
        return str(datetime.now().date())

async def import_data():
    db = get_db()
    
    for row in DATA:
        print(f"Processing {row['first_name']} {row['last_name']}...")
        
        # 1. Client
        full_name = f"{row['first_name']} {row.get('middle_name') or ''} {row['last_name']}".strip()
        client_data = {
            "full_name": full_name,
            "email": row["client_email"],
            "phone": row.get("phone") or None,
            "address": row.get("address") or None,
            "title": row.get("title") or None,
            "middle_name": row.get("middle_name") or None,
            "gender": row.get("gender") or None,
            "dob": row.get("dob") or None,
            "marital_status": row.get("marital") or None,
            "occupation": row.get("occupation") or None,
            "nin": row.get("nin") or None,
            "id_number": row.get("id_number") or None,
            "id_document_url": row.get("id_doc") or None,
            "nationality": row.get("nationality") or None,
            "passport_photo_url": row.get("passport_photo") or None,
            "nok_name": row.get("nok_name") or None,
            "nok_phone": row.get("nok_phone") or None,
            "nok_email": row.get("nok_email") or None,
            "nok_occupation": row.get("nok_occupation") or None,
            "nok_relationship": row.get("nok_relationship") or None,
            "nok_address": row.get("nok_address") or None,
            "source_of_income": row.get("income") or None,
            "referral_source": row.get("referral") or None
        }
        
        # Upsert client
        print(f" Checking client existence for {row['client_email']}...")
        client_res = db.table("clients").select("*").eq("email", row["client_email"]).execute()
        if client_res.data:
            client_id = client_res.data[0]["id"]
            print(f" Updating existing client {client_id}...")
            db.table("clients").update(client_data).eq("id", client_id).execute()
        else:
            print(f" Inserting new client...")
            new_client = db.table("clients").insert(client_data).execute()
            client_id = new_client.data[0]["id"]
            
        # 2. Invoice
        print(f" Generating invoice number...")
        invoice_number = db.rpc("generate_invoice_number").execute().data
        
        deposit = clean_amount(row.get("deposit"))
        outstanding = clean_amount(row.get("outstanding"))
        total_amount = deposit + outstanding
        
        # Clean plot size
        plot_size_numeric = None
        if row.get("plot_size"):
            cleaned_size = re.sub(r'[^\d.]+', '', row["plot_size"])
            if cleaned_size:
                try: plot_size_numeric = float(cleaned_size)
                except: pass
                
        # Pay date
        pay_date = parse_date(row.get("pay_date"))
        
        invoice_insert = {
            "invoice_number": invoice_number,
            "client_id": client_id,
            "property_name": row.get("property_name") or None,
            "plot_size_sqm": plot_size_numeric,
            "amount": total_amount,
            "amount_paid": deposit,
            "payment_terms": "Installment" if outstanding > 0 else "Outright",
            "invoice_date": pay_date,
            "due_date": pay_date,
            "sales_rep_name": row.get("rep_name") or None,
            "co_owner_name": row.get("co_owner_name") or None,
            "co_owner_email": row.get("co_owner_email") or None,
            "signature_url": row.get("signature") or None,
            "payment_proof_url": row.get("pay_proof") or None,
            "passport_photo_url": row.get("passport_photo") or None,
            "source": "spreadsheet_import"
        }
        
        print(f" Inserting invoice {invoice_number} for client {client_id}...")
        invoice_res = db.table("invoices").insert(invoice_insert).execute()
        invoice_id = invoice_res.data[0]["id"]
        
        # 3. Payment
        if deposit > 0:
            db.table("payments").insert({
                "invoice_id": invoice_id,
                "client_id": client_id,
                "reference": f"IMPORT_{pay_date}_{row['last_name']}",
                "amount": deposit,
                "payment_method": "Bank Transfer",
                "payment_date": pay_date,
                "notes": "Imported from spreadsheet"
            }).execute()
            
        # 4. Pending Verification
        if row["pay_proof"]:
            db.table("pending_verifications").insert({
                "invoice_id": invoice_id,
                "client_id": client_id,
                "payment_proof_url": row["pay_proof"],
                "deposit_amount": deposit,
                "payment_date": pay_date,
                "sales_rep_name": row["rep_name"],
                "status": "pending"
            }).execute()
            
        print(f"✅ Successfully imported {full_name} (Inv: {invoice_number})")

if __name__ == "__main__":
    asyncio.run(import_data())

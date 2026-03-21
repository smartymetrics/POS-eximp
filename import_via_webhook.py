import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

URL = "http://localhost:8005/api/webhooks/form-submission"
SECRET = os.getenv("WEBHOOK_SECRET")

DATA = [
    {
        "timestamp": "2025-12-18T15:58:33Z",
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
        "co_owner_name": "None",
        "co_owner_email": "None",
        "signature_url": "https://drive.google.com/open?id=1MJ0LVcN3NL5yr-bf6bXGDDUl7964Ye55",
        "plot_size": "500 SQM",
        "payment_duration": "6 months",
        "deposit_amount": 0,
        "total_amount": 0,
        "payment_date": None,
        "payment_proof_url": None,
        "payment_terms": "Outright",
        "source_of_income": "Business Income",
        "referral_source": "Referral",
        "consent": "I Confirm and Agree",
        "sales_rep_name": None,
        "sales_rep_phone": None
    },
    {
        "timestamp": "2025-12-29T07:00:57Z",
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
        "nationality": "Nigerian",
        "property_name": "Coinfield Estate",
        "nok_name": "Mbaogu Martins Ewezugachi",
        "nok_phone": "+2348165288460",
        "nok_relationship": "Sibling",
        "nok_address": "No 3 Chief Boniface Avenue Izuoma Asa New Layout, Oyigbo Rivers State",
        "ownership_type": "Sole Owner",
        "co_owner_name": "Charles Chiakpaoke Mbaogu",
        "co_owner_email": "doncharles376@gmail.com",
        "signature_url": "https://drive.google.com/open?id=1pys3NdNzvKk9L9HnBEtAueFoEbQz2SwL",
        "plot_size": "1000 SQM",
        "payment_duration": "6 months",
        "deposit_amount": 0,
        "total_amount": 0,
        "payment_date": None,
        "payment_proof_url": None,
        "payment_terms": "Outright",
        "source_of_income": "Business Income",
        "referral_source": "Salesperson",
        "consent": "I Confirm and Agree",
        "sales_rep_name": None
    },
    {
        "timestamp": "2025-12-31T18:04:33Z",
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
        "nationality": "Nigerian",
        "property_name": "Coinfield Estate",
        "nok_name": "Mbaogu Donatus Mgboatuchi",
        "nok_phone": "08132252759",
        "nok_email": "atuchimbaogu@gmail.com",
        "nok_relationship": "Child",
        "nok_address": "Plot 10 WTC Estate Enugu",
        "ownership_type": "Sole Owner",
        "co_owner_name": "Donatus Okechukwu Mbaogu",
        "co_owner_email": "mbaogudona@gmail.com",
        "signature_url": "https://drive.google.com/open?id=1Mn8lxYhsY1jiUUuewOobPlGxjlAL1YX_",
        "plot_size": "500 SQM",
        "payment_duration": "6 months",
        "deposit_amount": 0,
        "total_amount": 0,
        "payment_date": None,
        "payment_proof_url": None,
        "payment_terms": "Outright",
        "source_of_income": "Personal Income",
        "referral_source": "Other",
        "consent": "I Confirm and Agree",
        "sales_rep_name": None
    },
    {
        "timestamp": "2026-03-18T17:37:10Z",
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
        "nok_relationship": "Sibling",
        "nok_address": "No 12 dele Oladipo street, agotapa Moniya Ibadan",
        "ownership_type": "Sole Owner",
        "co_owner_name": None,
        "co_owner_email": None,
        "signature_url": "https://drive.google.com/open?id=1Sei-tHgFFWRwe44_pOK2CINOWKey8zRR",
        "plot_size": "300 SQM",
        "payment_duration": "3 months",
        "deposit_amount": 200000,
        "total_amount": 650000,
        "payment_date": "2026-03-18",
        "payment_proof_url": "https://drive.google.com/open?id=1D7kFv_IEZN2EHxIc-yfhG37Lw0bZs_0E",
        "payment_terms": "Installment",
        "source_of_income": "Loan",
        "referral_source": "Referral",
        "consent": "I Confirm and Agree",
        "sales_rep_name": None
    }
]

def import_data():
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Secret": SECRET
    }
    
    for row in DATA:
        print(f"Sending {row['first_name']} {row['last_name']} to webhook...")
        try:
            resp = requests.post(URL, json=row, headers=headers, timeout=30)
            if resp.status_code == 200:
                print(f" ✅ Success: {resp.json().get('status')}")
            else:
                print(f" ❌ Failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f" ❌ Connection Error: {e}")

if __name__ == "__main__":
    import_data()

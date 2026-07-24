import asyncio
import csv
import os
import sys
import re
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from database import get_db, db_execute
from models import WebhookFormPayload
from routers.webhooks import form_submission
from fastapi import Request, BackgroundTasks

class MockRequest:
    def __init__(self):
        self.headers = {"X-Webhook-Secret": os.getenv("WEBHOOK_SECRET")}

class MockBackgroundTasks(BackgroundTasks):
    def __init__(self):
        super().__init__()
        self.tasks = []
        
    def add_task(self, func, *args, **kwargs):
        # We run the background task synchronously here for the script to ensure it completes
        task = asyncio.create_task(func(*args, **kwargs))
        self.tasks.append(task)
        
    async def wait_all(self):
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

def get_val(row, keys):
    for key in keys:
        if key in row and row[key].strip():
            return row[key].strip()
    return ""

def strip_currency(val):
    if not val: return "0"
    cleaned = re.sub(r'[^\d.]+', '', val)
    return cleaned if cleaned else "0"

async def process_csv():
    db = get_db()
    
    with open("google_form_responses.csv", mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    print(f"Loaded {len(rows)} rows from CSV.")
    success_count = 0
    skip_count = 0
    
    for i, row in enumerate(rows):
        email = get_val(row, ["Email Address", "Client's email address", "Email Column", "Email"])
        first_name = get_val(row, ["Customer first name", "First Name"])
        last_name = get_val(row, ["Customer last name (surname)", "Last Name"])
        
        if not email:
            continue
            
        full_name = f"{first_name} {last_name}".strip()
        
        # 1. Check if client exists
        client_res = await db_execute(lambda: db.table("clients").select("id").eq("email", email).execute())
        
        if client_res.data:
            client_id = client_res.data[0]["id"]
            # 2. Check if they already have an active invoice
            inv_res = await db_execute(lambda: db.table("invoices").select("id, status").eq("client_id", client_id).execute())
            
            has_active_invoice = False
            for inv in inv_res.data:
                if inv.get("status") != "voided":
                    has_active_invoice = True
                    break
                    
            if has_active_invoice:
                # They already have an active invoice, skip to avoid duplicates
                skip_count += 1
                continue
                
        # If we reach here, either client doesn't exist, or client exists but has no invoice.
        # This means the webhook failed previously!
        
        print(f"\nProcessing failed submission for: {full_name} ({email})")
        
        payload_dict = {
            "title": get_val(row, ["Title"]),
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": get_val(row, ["Customer middle name", "Middle Name"]),
            "gender": get_val(row, ["Gender"]),
            "dob": get_val(row, ["Date of Birth", "DOB"]),
            "address": get_val(row, ["Client's residential address", "Residential Address"]),
            "city": get_val(row, ["City"]),
            "state": get_val(row, ["State"]),
            "email": email,
            "marital_status": get_val(row, ["Marital Status"]),
            "phone": get_val(row, ["Client's phone number\n(Whatsapp line)", "Phone Number", "Phone"]),
            "occupation": get_val(row, ["Occupation"]),
            
            "nin": get_val(row, ["NIN"]),
            "id_number": get_val(row, ["International Passport No/NIN Number", "ID Number"]),
            "id_document_url": get_val(row, ["Upload NIN/International Passport", "Upload ID"]),
            "nationality": get_val(row, ["Nationality"]),
            "passport_photo_url": get_val(row, ["Upload a passport photograph", "Upload Passport"]),
            
            "nok_name": get_val(row, ["Next of kin's full name", "Next of Kin Name"]),
            "nok_phone": get_val(row, ["Next of kin phone number", "Next of Kin Phone"]),
            "nok_email": get_val(row, ["Next of kin's email address", "Next of Kin Email"]),
            "nok_occupation": get_val(row, ["Next of kin's occupation", "Next of Kin Occupation"]),
            "nok_relationship": get_val(row, ["Relationship", "Next of Kin Relationship"]),
            "nok_address": get_val(row, ["Next of kin's home address", "Next of Kin Address"]),
            
            "ownership_type": get_val(row, ["Ownership Type"]),
            "co_owner_name": get_val(row, ['"Full name of the Second Owner\n(Surname, First name, Other Name)"', 'Full name of the Second Owner\n(Surname, First name, Other Name)', 'Full name of the Second Owner']),
            "co_owner_email": get_val(row, ["Email address (Co-owner)"]),
            "signature_url": get_val(row, ["Upload Signature"]),
            "signature_base64": "",
            
            "property_name": get_val(row, ["Property name", "Property Name"]),
            "plot_size": get_val(row, ["Plot size", "Plot Size"]),
            "quantity": int(get_val(row, ["Quantity"]) or 1),
            
            "payment_duration": get_val(row, ["Payment Duration"]),
            "deposit_amount": float(strip_currency(get_val(row, ["Deposit Made (In Naira)", "Deposit"]))),
            "total_amount": float(strip_currency(get_val(row, ["Total Selling Price", "Property Price"]))),
            "payment_date": get_val(row, ["Date of Payment/Deposit ", "Payment Date", "Date of Payment/Deposit"]),
            "payment_proof_url": get_val(row, ["Upload receipt of payment/deposit", "Payment Proof"]),
            "payment_terms": get_val(row, ["Payment Duration"]) or "Outright",
            
            "source_of_income": get_val(row, ["Source of Income"]),
            "referral_source": get_val(row, ["How did you get to know about our property", "How did you hear about us?"]),
            "purchase_purpose": get_val(row, ["Is this property being purchased:", "Purchase Purpose"]),
            "sales_rep_name": get_val(row, ["Sales Rep / Marketer Name  ", "Sales Rep / Marketer Name", "Sales Rep Name"]),
            "sales_rep_phone": get_val(row, ["Sales Rep Phone Number"]),
            "consent": get_val(row, ['"By checking this box, I confirm that I have read, understand, and consent to all of the following Eximp & Cloves Infrastructure limited documents: Terms and Conditions, Payment Protection Promise and Refund Policies. I accept full responsibility for all legal implications and interpretations of this agreement. I understand that this subscription form becomes binding on all parties immediately upon the company\'s receipt of my payment.  "', 'By checking this box, I confirm that I have read, understand, and consent to all of the following Eximp & Cloves Infrastructure limited documents: Terms and Conditions, Payment Protection Promise and Refund Policies. I accept full responsibility for all legal implications and interpretations of this agreement. I understand that this subscription form becomes binding on all parties immediately upon the company\'s receipt of my payment.  ', 'Consent Checkbox']),
            
            "submitter_email": email,
            "timestamp": get_val(row, ["Timestamp"])
        }
        
        try:
            payload = WebhookFormPayload(**payload_dict)
            req = MockRequest()
            bg = MockBackgroundTasks()
            
            res = await form_submission(payload, req, bg)
            print(f" -> Success! Created Invoice: {res.get('invoice_number')}")
            success_count += 1
            
            # Wait a moment for background tasks (emails) to dispatch
            await asyncio.sleep(2)
            print(f" -> Waiting for background tasks (emails) to finish...")
            await bg.wait_all()
            print(f" -> Finished processing {email}")
            
        except Exception as e:
            print(f" -> ERROR processing {email}: {e}")

    print("\n==============================")
    print("IMPORT COMPLETE")
    print(f"Successfully processed: {success_count}")
    print(f"Skipped (Already had invoice): {skip_count}")
    print("==============================")

if __name__ == "__main__":
    asyncio.run(process_csv())

import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from database import get_db, db_execute
from models import WebhookFormPayload
from routers.webhooks import form_submission
from fastapi import Request, BackgroundTasks

class MockRequest:
    def __init__(self):
        self.headers = {"X-Webhook-Secret": os.getenv("WEBHOOK_SECRET")}

class MockBackgroundTasks(BackgroundTasks):
    def add_task(self, func, *args, **kwargs):
        print("Background task scheduled:", func.__name__)

async def run():
    payload_dict = {
        "timestamp": "2026-05-04T23:33:47Z",
        "email": "omichworld@gmail.com",
        "passport_photo_url": "https://drive.google.com/open?id=10WbIyBfPfEawiL_GwxlZSDWn3mp1Rv27",
        "title": "Miss",
        "first_name": "Feyisara",
        "last_name": "Abiola",
        "middle_name": "Racheal",
        "gender": "Female",
        "dob": "1999-10-26",
        "address": "55, Abule oko road, Magboro.",
        "phone": "08131832073",
        "occupation": "Fashion designer",
        "marital_status": "Single",
        "nin": "68518581301",
        "id_number": "68518581301",
        "id_document_url": "https://drive.google.com/open?id=1j7P9tOhJkBv711ItlZRWVo16O7nFBEZI",
        "nationality": "Nigeria",
        "property_name": "Mokoloki Ofada Mowe",
        "nok_name": "Abiola Oluwatobiloba gideon",
        "nok_phone": "+13065013668",
        "nok_email": "Abiolatobi3927@gmail.com",
        "nok_occupation": "Mechanical engineer",
        "nok_relationship": "Sibling",
        "nok_address": "1761 mustard street, Saskatchewan, Canada.",
        "ownership_type": "I want to add another name to the property (co-owner)",
        "co_owner_name": "Abiola Oluwatobiloba Gideon",
        "co_owner_email": "Abiolatobi3927@gmail.com",
        "signature_url": "https://drive.google.com/open?id=10MWZetaSl-9xbjdTLjbmlJkNW87m4kBA",
        "plot_size": "500 SQM",
        "payment_duration": "Outright",
        "deposit_amount": 1800000,
        "total_amount": 0,
        "payment_date": "2026-05-02",
        "payment_proof_url": "https://drive.google.com/open?id=1UB-iHOq-FUqGOjo-ORl6-6Q1N8bXmDsU",
        "payment_terms": "Outright",
        "source_of_income": "Personal Income",
        "referral_source": "Salesperson",
        "consent": "I Confirm and Agree",
        "sales_rep_name": "Omich",
        "sales_rep_phone": "08131832073",
        "quantity": 1
    }
    
    payload = WebhookFormPayload(**payload_dict)
    req = MockRequest()
    bg = MockBackgroundTasks()
    
    try:
        res = await form_submission(payload, req, bg)
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(run())

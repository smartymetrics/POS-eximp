import requests
import json
import os

# Mock Configuration
SECRET = "eximp_cloves_form_web_2026_xyz"
URL = "http://localhost:8000/api/webhooks/form-submission"

# Mock Payload matching appscript.js and models.py
payload = {
    "title": "Mr",
    "first_name": "Diagnostic",
    "last_name": "Test",
    "middle_name": "User",
    "gender": "Male",
    "dob": "1990-01-01",
    "address": "123 Diagnostic Lane",
    "city": "Lagos",
    "state": "Lagos",
    "email": "diag_test@example.com",
    "phone": "08012345678",
    "marital_status": "Single",
    "occupation": "Automated Tester",
    "nin": "12345678901",
    "id_number": "A00123456",
    "nationality": "Nigerian",
    
    # Ownership
    "ownership_type": "Personal",
    "consent": "I Confirm and Agree to the terms",
    
    # Property
    "property_name": "Coinfield Estate", # Assuming this exists or using fuzzy match
    "plot_size": "500sqm",
    "quantity": 1,
    
    # Payment
    "payment_duration": "Outright",
    "deposit_amount": 1500000.0,
    "total_amount": 5000000.0,
    "payment_date": "2026-03-30",
    "payment_terms": "Outright",
    
    # Other
    "sales_rep_name": "Smarty Chuks",
    "referral_source": "Facebook",
    "purchase_purpose": "Investment",
    "timestamp": "2026-03-30T10:00:00Z"
}

headers = {
    "Content-Type": "application/json",
    "X-Webhook-Secret": SECRET
}

print(f"--- DIAGNOSTIC WEBHOOK TEST ---")
print(f"Target URL: {URL}")
print(f"Using Secret: {SECRET}")

try:
    response = requests.post(URL, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS: Webhook logic processing successfully.")
    else:
        print("\n❌ FAILURE: Check console logs for errors.")
except Exception as e:
    print(f"Error: {e}")

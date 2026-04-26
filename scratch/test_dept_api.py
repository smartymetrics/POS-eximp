import requests
import json

BASE_URL = "http://localhost:8000/api/hr/departments-v2"
# You might need a token, but let's see if it 405s first
# Or just try to hit it with GET to confirm the URL is correct

try:
    print("Testing GET...")
    r = requests.get(BASE_URL)
    print(f"GET Status: {r.status_code}")
    
    print("\nTesting POST...")
    # Sending a dummy payload
    r = requests.post(BASE_URL, json={"name": "Test Dept"})
    print(f"POST Status: {r.status_code}")
    print(f"POST Body: {r.text}")
except Exception as e:
    print(f"Error: {e}")

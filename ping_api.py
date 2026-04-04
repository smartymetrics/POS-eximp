import urllib.request
import urllib.parse
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print("[1] Logging in...")
data = json.dumps({"email": "admin@eximps-cloves.com", "password": "getdagold"}).encode('utf-8')
req = urllib.request.Request("http://127.0.0.1:8000/auth/login", data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        result = json.loads(response.read().decode())
        token = result['access_token']
        print("[2] Logged in successfully. Targetting segmentation endpoint...")
        
        req2 = urllib.request.Request("http://127.0.0.1:8000/api/marketing/segments/diagnostic/financial-segmentation", headers={'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(req2, context=ctx) as response2:
             stats = json.loads(response2.read().decode())
             print("[3] Result:", json.dumps(stats, indent=2))
except Exception as e:
    print("FAILED:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())

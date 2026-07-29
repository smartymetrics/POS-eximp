import sys
import os
import requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.stdout.reconfigure(encoding='utf-8')

urls = {
    "client_sig_cloudinary": "https://res.cloudinary.com/f046mie1/image/upload/v1784964614/signatures/contracts/1ee906f6-f2c6-4994-b93f-bbaea4ede474/client.png.png",
    "witness_sig_supabase": "https://scsdnstqtrqjsosbmxyf.supabase.co/storage/v1/object/public/signatures/witnesses/1ee906f6-f2c6-4994-b93f-bbaea4ede474/witness1.png",
    "client_drive_url": "https://drive.google.com/open?id=1Sei-tHgFFWRwe44_pOK2CINOWKey8zRR"
}

for name, url in urls.items():
    print(f"\n--- Testing {name} ---")
    print("URL:", url)
    try:
        res = requests.get(url, timeout=10)
        print("Status code:", res.status_code)
        print("Content-Type:", res.headers.get("Content-Type"))
        print("Content-Length:", len(res.content))
        if res.status_code != 200:
            print("Response body snippet:", res.text[:200])
    except Exception as e:
        print("Error:", e)

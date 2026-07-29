import sys, os
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import supabase
import requests

real_storage = supabase.storage._real_storage
bucket = "Cloud Infrastructure"
path = "portal_claims/2cecedd1-2209-47aa-aa30-6d67e4ba7a0a_c4fea747b2754c0fb2ebcd2753f781d1.png"

print("--- Testing Supabase Storage ---")
try:
    download_res = real_storage.from_(bucket).download(path)
    print(f"[OK] Supabase download success! File size: {len(download_res)} bytes")
except Exception as e:
    print(f"[FAIL] Supabase download failed: {e}")

try:
    signed_res = real_storage.from_(bucket).create_signed_url(path, 3600)
    print("Supabase signed URL result:", signed_res)
    url = signed_res.get("signedURL") or signed_res.get("signed_url")
    if url:
        resp = requests.get(url)
        print(f"HTTP GET to Supabase signed URL: Status {resp.status_code}, Content-Length: {len(resp.content)} bytes")
except Exception as e:
    print(f"[FAIL] Supabase signed URL error: {e}")

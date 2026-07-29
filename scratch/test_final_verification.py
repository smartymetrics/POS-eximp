import sys, os
# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage_service import generate_signed_url
import requests
from database import get_db

db = get_db()
res = db.table("expenditure_requests").select("id, title, receipt_url").not_.is_("receipt_url", "null").limit(10).execute()

print("--- Final Verification Test ---")
ok = 0
missing = 0
space_err = 0

for r in (res.data or []):
    raw = r["receipt_url"]
    print(f"\nRequest {r['id']} ({r.get('title')}):")

    paths = [raw]
    if raw.startswith("["):
        import json
        paths = json.loads(raw)

    for p in paths:
        url = generate_signed_url("Cloud Infrastructure", p)
        if not url:
            print(f"  [MISSING] Path '{p}' -> file missing from all backends")
            missing += 1
            continue

        has_space = " " in url
        has_encoded = "%20" in url
        print(f"  Path: {p}")
        print(f"  URL (first 100): {url[:100]}...")
        print(f"  Raw space in URL: {has_space}   |   %20 in URL: {has_encoded}")

        if has_space:
            space_err += 1

        try:
            resp = requests.get(url, timeout=10)
            status = resp.status_code
            size = len(resp.content)
            print(f"  HTTP GET: {status}  ({size} bytes)")
            if status != 200:
                print(f"  [WARN] Unexpected status {status}")
            else:
                ok += 1
        except requests.exceptions.Timeout:
            print("  [WARN] Request timed out (10s)")
        except Exception as e:
            print(f"  [ERROR] Request error: {e}")

print(f"\n{'='*50}")
print(f"[OK]  Accessible files  : {ok}")
print(f"[--]  Missing files     : {missing}")
print(f"[ERR] Space encode errs : {space_err}")
if space_err == 0:
    print("[OK]  All URLs are properly encoded (no raw spaces).")
else:
    print(f"[ERR] {space_err} URL(s) still contain raw spaces!")

import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from database import get_db
import cloudinary_client as cc
import cloudinary.api
import requests as req

db = get_db()

TARGET_ID = "e90c3926-5909-44be-9694-eaf462c08ce5"

print(f"=== Investigating Expenditure Request: {TARGET_ID[:8]}... ===\n")

res = db.table("expenditure_requests").select("*").eq("id", TARGET_ID).execute()
if not res.data:
    print("[ERROR] Record not found")
    exit(1)

row = res.data[0]
print(f"Title        : {row.get('title')}")
print(f"Status       : {row.get('status')}")
print(f"Created at   : {row.get('created_at')}")
print(f"receipt_url  : {row.get('receipt_url')}")
print(f"proforma_url : {row.get('proforma_url')}")
print()

import json

def check_file(label, raw_path):
    if not raw_path:
        print(f"{label}: <empty>")
        return

    paths = [raw_path]
    if raw_path.startswith("["):
        try:
            paths = json.loads(raw_path)
        except Exception:
            pass

    for p in paths:
        print(f"\n{label}: {p}")

        # 1. Check Cloudinary via Admin API (authoritative)
        try:
            resource = cloudinary.api.resource(
                f"Cloud Infrastructure/{p}",
                resource_type="image",
                type="authenticated"
            )
            print(f"  [CLOUDINARY ADMIN] FOUND - public_id: {resource.get('public_id')}, created: {resource.get('created_at')}")
        except Exception as e:
            err = str(e)
            if "not found" in err.lower() or "Resource not found" in err:
                print(f"  [CLOUDINARY ADMIN] NOT FOUND (404)")
            else:
                print(f"  [CLOUDINARY ADMIN] Error: {err[:80]}")

        # 2. Check CDN HEAD probe (what hybrid_storage uses)
        resource_cdn = cc.resource_exists("Cloud Infrastructure", p)
        print(f"  [CDN PROBE]        {'FOUND -> ' + str(resource_cdn) if resource_cdn else 'NOT FOUND (returns None)'}")

        # 3. Check if it exists in Supabase by trying to sign a URL
        try:
            from database import supabase
            real_storage = supabase.storage._real_storage
            res2 = real_storage.from_("Cloud Infrastructure").create_signed_url(p, 60)
            signed = res2.get("signedURL") or res2.get("signed_url") if isinstance(res2, dict) else str(res2)
            if signed:
                resp = req.head(signed, timeout=5)
                print(f"  [SUPABASE]         {'FOUND (HTTP ' + str(resp.status_code) + ')' if resp.status_code == 200 else 'HTTP ' + str(resp.status_code)}")
            else:
                print(f"  [SUPABASE]         No signed URL returned")
        except Exception as e:
            err = str(e)
            if "not_found" in err or "Object not found" in err:
                print(f"  [SUPABASE]         NOT FOUND")
            else:
                print(f"  [SUPABASE]         Error: {err[:80]}")

check_file("receipt_url ", row.get("receipt_url"))
check_file("proforma_url", row.get("proforma_url"))

print("\nDone.")

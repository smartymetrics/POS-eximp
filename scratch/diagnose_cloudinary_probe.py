import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import cloudinary
import cloudinary.utils
import cloudinary_client as cc
from database import get_db

db = get_db()

# Get a few expenditure receipt paths
res = db.table("expenditure_requests").select("id, receipt_url").not_.is_("receipt_url", "null").limit(3).execute()

print("=== CDN HEAD Probe Diagnosis ===\n")
for r in (res.data or []):
    raw = r["receipt_url"]
    path = raw
    if raw.startswith("["):
        import json
        paths = json.loads(raw)
        path = paths[0] if paths else None
    if not path:
        continue

    bucket = "Cloud Infrastructure"
    print(f"File: {path[:60]}...")

    # Try both delivery types and resource types
    for d_type in ("authenticated", "upload"):
        for rtype in ("image", "raw"):
            for public_id in cc.cloudinary_public_ids(bucket, path, rtype):
                try:
                    url, _ = cloudinary.utils.cloudinary_url(
                        public_id,
                        resource_type=rtype,
                        type=d_type,
                        sign_url=(d_type == "authenticated"),
                        secure=True,
                    )
                    resp = requests.head(url, timeout=5, allow_redirects=True)
                    print(f"  [{d_type}/{rtype}] public_id={public_id[:50]} => HTTP {resp.status_code}")
                    if resp.status_code == 200:
                        print(f"    URL: {url[:80]}...")
                        break
                except Exception as e:
                    print(f"  [{d_type}/{rtype}] ERROR: {e}")
    print()

print("Done.")

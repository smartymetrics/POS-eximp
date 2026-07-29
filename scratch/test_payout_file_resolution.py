import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
logging.basicConfig(level=logging.INFO)

from storage_service import generate_signed_url
from hybrid_storage import HybridStorage
import cloudinary_client as cc
from database import get_db

db = get_db()
res = db.table("expenditure_requests").select("id, title, receipt_url").not_.is_("receipt_url", "null").limit(10).execute()

for r in res.data or []:
    raw = r["receipt_url"]
    print(f"\nRequest {r['id']} ({r.get('title')}):")
    print(f"  Raw DB path: {raw}")
    
    paths = [raw]
    if raw.startswith("["):
        import json
        paths = json.loads(raw)
        
    for p in paths:
        print(f"  Checking path: '{p}'")
        # Check resource in Cloudinary directly
        res_c = cc.resource_exists("Cloud Infrastructure", p)
        print(f"    Cloudinary resource_exists: {bool(res_c)}")
        if res_c:
            print(f"    Cloudinary public_id: {res_c.get('public_id')}, type: {res_c.get('type')}, format: {res_c.get('format')}")
            signed_c = cc.build_url("Cloud Infrastructure", p, res_c)
            print(f"    Cloudinary URL: {signed_c}")
        
        # Test full generate_signed_url
        signed = generate_signed_url("Cloud Infrastructure", p)
        print(f"    generate_signed_url result: {signed}")

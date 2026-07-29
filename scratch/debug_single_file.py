import sys, os
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cloudinary_client as cc
import cloudinary.api

bucket = "Cloud Infrastructure"
path = "portal_claims/2cecedd1-2209-47aa-aa30-6d67e4ba7a0a_c4fea747b2754c0fb2ebcd2753f781d1.png"

print("--- Testing resource_exists ---")
res = cc.resource_exists(bucket, path)
print("resource_exists result:", res)

print("\n--- Direct Admin API Probing ---")
types_to_try = ["authenticated", "upload"]
rtypes_to_try = ["image", "raw"]
public_ids_to_try = cc.cloudinary_public_ids(bucket, path, "image") + cc.cloudinary_public_ids(bucket, path, "raw")

for t in types_to_try:
    for rt in rtypes_to_try:
        for pid in public_ids_to_try:
            try:
                out = cloudinary.api.resource(pid, resource_type=rt, type=t)
                print(f"✅ FOUND! type={t}, resource_type={rt}, public_id='{pid}'")
                print("   URL:", out.get("secure_url"))
            except Exception as e:
                print(f"❌ Failed type={t}, resource_type={rt}, public_id='{pid}': {e}")

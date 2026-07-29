import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cloudinary
import cloudinary.api

print("=== Cloudinary Admin API: Search for portal_claims assets ===\n")

# Search for any resource with Cloud Infrastructure in its public_id
# Try different prefix formats to see how Cloudinary actually stored the bucket name
for prefix in ("Cloud Infrastructure", "Cloud_Infrastructure", "Cloud%20Infrastructure"):
    try:
        result = cloudinary.api.resources(
            type="authenticated",
            resource_type="image",
            prefix=prefix,
            max_results=5,
        )
        found = result.get("resources", [])
        print(f"Prefix '{prefix}' (authenticated/image): {len(found)} found")
        for r in found:
            print(f"  public_id: {r['public_id']}")
    except Exception as e:
        print(f"Prefix '{prefix}' (authenticated/image): ERROR {e}")

    try:
        result = cloudinary.api.resources(
            type="upload",
            resource_type="image",
            prefix=prefix,
            max_results=5,
        )
        found = result.get("resources", [])
        print(f"Prefix '{prefix}' (upload/image): {len(found)} found")
        for r in found:
            print(f"  public_id: {r['public_id']}")
    except Exception as e:
        print(f"Prefix '{prefix}' (upload/image): ERROR {e}")

    print()

# Also check total resource count
try:
    usage = cloudinary.api.usage()
    print(f"Account usage: {usage.get('resources', 'N/A')} total resources on Cloudinary")
except Exception as e:
    print(f"Usage check error: {e}")

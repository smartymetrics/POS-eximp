import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from storage_service import upload_portal_file, generate_signed_url, PORTAL_CLAIMS_BUCKET
import cloudinary_client as cc

# Create a tiny test PNG (1x1 white pixel) via PIL or hardcoded valid bytes
import struct, zlib

def make_1x1_png():
    def chunk(name, data):
        c = struct.pack('>I', len(data)) + name + data
        return c + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    raw = b'\x00\xff\xff\xff'  # filter byte + RGB white
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

TEST_PNG = make_1x1_png()

TEST_PATH = "portal_claims/_upload_test_DO_NOT_USE.png"

print(f"=== Upload Test to Cloudinary ===")
print(f"Bucket : {PORTAL_CLAIMS_BUCKET}")
print(f"Path   : {TEST_PATH}")
print(f"Size   : {len(TEST_PNG)} bytes")
print()

# Test 1: Direct cc.upload_bytes
print("--- Step 1: Direct cloudinary_client.upload_bytes ---")
try:
    result = cc.upload_bytes(PORTAL_CLAIMS_BUCKET, TEST_PATH, TEST_PNG, "image/png")
    print(f"[OK] Cloudinary upload succeeded")
    print(f"     public_id  : {result.get('public_id')}")
    print(f"     secure_url : {result.get('secure_url', '')[:80]}...")
    print(f"     type       : {result.get('type')}")
    print(f"     resource_type: {result.get('resource_type')}")
except Exception as e:
    print(f"[FAIL] {type(e).__name__}: {e}")

print()

# Test 2: Via upload_portal_file (full stack)
print("--- Step 2: upload_portal_file (full HybridStorage stack) ---")
ok = upload_portal_file(TEST_PATH, TEST_PNG, "image/png")
print(f"Result: {'OK - uploaded' if ok else 'FAILED'}")

print()

# Test 3: Now check resource_exists (CDN HEAD probe)
print("--- Step 3: resource_exists CDN probe after upload ---")
resource = cc.resource_exists(PORTAL_CLAIMS_BUCKET, TEST_PATH)
if resource:
    print(f"[OK] Found on Cloudinary: {resource}")
else:
    print("[FAIL] resource_exists returned None — file not found via CDN probe")

print()

# Test 4: Generate signed URL
print("--- Step 4: generate_signed_url ---")
url = generate_signed_url(PORTAL_CLAIMS_BUCKET, TEST_PATH)
print(f"URL: {url[:100] if url else '<NONE>'}...")

# Cleanup
print()
print("--- Cleanup: deleting test file from Cloudinary ---")
try:
    deleted = cc.delete(PORTAL_CLAIMS_BUCKET, TEST_PATH)
    print(f"Deleted: {deleted}")
except Exception as e:
    print(f"Delete error: {e}")

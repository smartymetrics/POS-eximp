import os
import uuid
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Correct bucket name
BUCKET = "hr-documents"
TEST_FILE = f"test_{uuid.uuid4().hex}.txt"
TEST_CONTENT = b"Hello Supabase Storage"

try:
    print(f"Uploading to bucket '{BUCKET}'...")
    res = supabase.storage.from_(BUCKET).upload(
        path=TEST_FILE,
        file=TEST_CONTENT,
        file_options={"content-type": "text/plain", "upsert": "true"}
    )
    print(f"Upload result: {res}")
    
    print("Generating signed URL...")
    url_res = supabase.storage.from_(BUCKET).create_signed_url(TEST_FILE, 3600)
    print(f"Signed URL result: {url_res}")
    
except Exception as e:
    print(f"Error: {e}")

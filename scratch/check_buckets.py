import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

try:
    buckets = supabase.storage.list_buckets()
    print("Buckets found:")
    for b in buckets:
        print(f"- {b.name}")
except Exception as e:
    print(f"Error listing buckets: {e}")

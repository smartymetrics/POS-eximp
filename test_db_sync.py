import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"Connecting to {url}...")
# Note: Using Client[any] to avoid typing issues if any
supabase = create_client(url, key)

try:
    print("Fetching one admin...")
    res = supabase.table("admins").select("id, full_name").limit(1).execute()
    print(f"Result: {res.data}")
except Exception as e:
    print(f"Error: {e}")

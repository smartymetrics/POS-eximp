import os
from dotenv import load_dotenv
from database import SUPABASE_URL, SUPABASE_SERVICE_KEY

print(f"URL: {SUPABASE_URL}")
print(f"KEY: {SUPABASE_SERVICE_KEY[:20]}...")
print(f"CWD: {os.getcwd()}")

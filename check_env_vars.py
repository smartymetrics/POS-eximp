import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"URL: {url}")
print(f"KEY_LENGTH: {len(key) if key else 0}")
print(f"CWD: {os.getcwd()}")

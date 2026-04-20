import os
import dotenv
from supabase import create_client

dotenv.load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
s = create_client(url, key)

print("--- SALES REPS ---")
res = s.table("sales_reps").select("id, name, email").execute()
for r in res.data:
    print(f"{r['name']} | {r['id']} | {r['email']}")

print("\n--- CLIENT SAMPLE ---")
res = s.table("clients").select("*").limit(1).execute()
if res.data:
    print(f"Columns: {list(res.data[0].keys())}")

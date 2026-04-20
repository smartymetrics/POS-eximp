import os
import dotenv
from supabase import create_client

dotenv.load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
s = create_client(url, key)

res = s.table("admins").select("id, full_name, email").execute()
for admin in res.data:
    print(f"{admin['full_name']} | {admin['id']} | {admin['email']}")

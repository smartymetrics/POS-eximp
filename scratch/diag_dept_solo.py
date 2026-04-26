import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Missing env vars")
    exit(1)

supabase: Client = create_client(url, key)

def check():
    print(f"URL: {url}")
    try:
        # Check if table exists
        print("Checking departments table...")
        res = supabase.table("departments").select("*").execute()
        print(f"Current rows: {len(res.data)}")
        
        # Try insert
        print("Testing insert...")
        ins = supabase.table("departments").insert({"name": "TEST_FROM_SCRIPT"}).execute()
        print(f"Insert success: {ins.data}")
        
        # Try delete
        if ins.data:
            print("Testing delete...")
            supabase.table("departments").delete().eq("id", ins.data[0]["id"]).execute()
            print("Delete success")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check()

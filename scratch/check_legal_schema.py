import os
from supabase import create_client

def check_schema():
    url = "https://scsdnstqtrqjsosbmxyf.supabase.co"
    key = os.environ.get("SUPABASE_KEY")
    if not key:
        print("SUPABASE_KEY not found in env")
        return

    supabase = create_client(url, key)
    
    # Try to fetch one row from legal_matters to see keys
    res = supabase.table("legal_matters").select("*").limit(1).execute()
    if res.data:
        print(f"Columns in legal_matters: {list(res.data[0].keys())}")
    else:
        print("No data in legal_matters to check columns.")

if __name__ == "__main__":
    check_schema()

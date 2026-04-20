import os
from supabase import create_client

def list_matters():
    url = "https://scsdnstqtrqjsosbmxyf.supabase.co"
    key = os.environ.get("SUPABASE_KEY")
    if not key:
        print("SUPABASE_KEY not found")
        return

    supabase = create_client(url, key)
    res = supabase.table("legal_matters").select("id, title, content_html").limit(10).execute()
    for m in res.data:
        length = len(m.get("content_html") or "")
        print(f"ID: {m['id']} | Title: {m['title']} | Content Length: {length}")

if __name__ == "__main__":
    list_matters()

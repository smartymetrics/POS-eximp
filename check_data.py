import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def check_data():
    print("--- CLIENTS ---")
    clients = supabase.table("clients").select("id, full_name, email").execute()
    for c in clients.data:
        inv_res = supabase.table("invoices").select("invoice_number").eq("client_id", c["id"]).execute()
        inv_nums = [i["invoice_number"] for i in inv_res.data]
        print(f"ID: {c['id']} | Name: {c['full_name']} | Email: {c['email']} | Invoices ({len(inv_nums)}): {', '.join(inv_nums)}")

    print("\n--- RECENT INVOICES ---")
    invoices = supabase.table("invoices").select("id, invoice_number, client_id").order("created_at", desc=True).limit(10).execute()
    for i in invoices.data:
        print(f"Inv: {i['invoice_number']} | ClientID: {i['client_id']}")

if __name__ == "__main__":
    check_data()

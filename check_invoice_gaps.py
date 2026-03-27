import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def get_all_invoices():
    all_invs = []
    limit = 1000
    offset = 0
    while True:
        res = supabase.table("invoices").select("invoice_number").order("invoice_number").range(offset, offset + limit - 1).execute()
        if not res.data:
            break
        all_invs.extend([r["invoice_number"] for r in res.data])
        offset += limit
    return all_invs

def find_gaps(inv_list):
    if not inv_list:
        return []
    
    # Extract numbers from EC-XXXXXX
    numbers = []
    for inv in inv_list:
        try:
            num = int(inv.split("-")[1])
            numbers.append(num)
        except:
            continue
            
    if not numbers:
        return []
        
    full_range = set(range(1, max(numbers) + 1))
    missing = full_range - set(numbers)
    return sorted(list(missing))

if __name__ == "__main__":
    inv_list = get_all_invoices()
    gaps = find_gaps(inv_list)
    print(f"Total gaps found: {len(gaps)}")
    print(f"Missing numbers: {gaps}")

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

if __name__ == "__main__":
    print("Analyzing client address data...")
    res = supabase.table("clients").select("address, city, state").execute()
    data = res.data
    
    total = len(data)
    yaba_lagos_with_address = 0
    yaba_lagos_no_address = 0
    others = 0
    
    for c in data:
        addr = (c.get("address") or "").lower().strip()
        city = (c.get("city") or "").lower().strip()
        state = (c.get("state") or "").lower().strip()
        
        has_addr = bool(addr)
        is_yaba_lagos = (city == "yaba" or state == "lagos")
        
        if is_yaba_lagos:
            if has_addr:
                yaba_lagos_with_address += 1
                print(f"SUSPICIOUS: Addr='{c['address']}', City='{c['city']}', State='{c['state']}'")
            else:
                yaba_lagos_no_address += 1
        else:
            others += 1
            
    print(f"\nSummary:")
    print(f"Total Clients: {total}")
    print(f"Yaba or Lagos (with other address): {yaba_lagos_with_address}")
    print(f"Yaba or Lagos (NO other address): {yaba_lagos_no_address}")
    print(f"Other / Genuine: {others}")

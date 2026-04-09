import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def sync_legacy_reps():
    print("Starting Legacy Sales Rep Sync (Paginated Mode)...")
    
    # 1. Fetch admins
    admins_url = f"{SUPABASE_URL}/rest/v1/admins?select=id,full_name&is_active=eq.true"
    r = requests.get(admins_url, headers=headers, timeout=120, verify=False)
    admins = r.json()
    
    # Pre-process admin names for better matching
    admin_list = []
    for a in admins:
        if not a.get("full_name"): continue
        name = a["full_name"].strip().lower()
        # Create a set of words for the admin name
        words = set(name.replace("mrs.", "").replace("mrs", "").replace("mr.", "").replace("mr", "").split())
        admin_list.append({
            "id": a["id"],
            "full_name": a["full_name"],
            "key": name,
            "words": words
        })
    print(f"Loaded {len(admin_list)} admins.")
    
    # 2. Fetch unassigned clients (including added_by)
    clients_url = f"{SUPABASE_URL}/rest/v1/clients?select=id,full_name,added_by&assigned_rep_id=is.null"
    r = requests.get(clients_url, headers=headers, timeout=120, verify=False)
    clients = r.json()
    print(f"Found {len(clients)} unassigned clients.")
    
    if not clients:
        print("Done! No unassigned clients found.")
        return

    # 3. Fetch latest invoices with sales reps AND created_by
    print("Fetching historical sales data in batches...")
    rep_lookup = {}
    creator_lookup = {}
    limit = 1000
    offset = 0
    while True:
        inv_url = f"{SUPABASE_URL}/rest/v1/invoices?select=client_id,sales_rep_name,created_by&order=created_at.desc&limit={limit}&offset={offset}"
        try:
            r = requests.get(inv_url, headers=headers, timeout=120, verify=False)
            batch = r.json()
        except Exception as e:
            print(f"Error fetching batch at offset {offset}: {e}")
            break
            
        if not batch: break
        
        for inv in batch:
            cid = inv["client_id"]
            if cid not in rep_lookup and inv.get("sales_rep_name"):
                rep_lookup[cid] = inv["sales_rep_name"].strip()
            if cid not in creator_lookup and inv.get("created_by"):
                creator_lookup[cid] = inv["created_by"]
        
        offset += limit
        print(f"Fetched {offset} invoices...")
        if len(batch) < limit: break

    updated_count = 0
    matched_reps = {}

    def find_best_match(rep_name):
        rep_name = rep_name.lower().replace("mrs.", "").replace("mrs", "").replace("mr.", "").replace("mr", "").strip()
        rep_words = set(rep_name.split())
        
        # 1. Try exact match
        for a in admin_list:
            if a["key"] == rep_name:
                return a["id"]
        
        # 2. Try word intersection
        best_match = None
        max_overlap = 0
        for a in admin_list:
            overlap = len(rep_words.intersection(a["words"]))
            if overlap > max_overlap:
                max_overlap = overlap
                best_match = a["id"]
        
        if max_overlap >= 1:
            return best_match
            
        return None

    print("Processing updates...")
    for client in clients:
        client_id = client["id"]
        admin_id = None
        
        # Priority 1: Legacy sales_rep_name
        rep_name = rep_lookup.get(client_id)
        if rep_name:
            admin_id = find_best_match(rep_name)
        
        # Priority 2: Invoice created_by (fallback)
        if not admin_id:
            admin_id = creator_lookup.get(client_id)
            
        # Priority 3: Client added_by (fallback)
        if not admin_id:
            admin_id = client.get("added_by")
        
        if admin_id:
            try:
                update_url = f"{SUPABASE_URL}/rest/v1/clients?id=eq.{client_id}"
                requests.patch(update_url, headers=headers, json={"assigned_rep_id": admin_id}, timeout=30, verify=False)
                updated_count += 1
                matched_reps["Matched"] = matched_reps.get("Matched", 0) + 1
            except Exception as e:
                print(f"Error updating client {client_id}: {e}")

    print("\n" + "="*40)
    print(f"Sync Complete!")
    print(f"Total Clients Updated: {updated_count}")
    print("Breakdown by Rep:")
    for rep, count in matched_reps.items():
        print(f" - {rep}: {count} clients")
    print("="*40)

if __name__ == "__main__":
    sync_legacy_reps()

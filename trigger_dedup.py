import os
from supabase import create_client

def deduplicate():
    # Attempt to load creds from .env
    from dotenv import load_dotenv
    load_dotenv('.env')
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        print("Missing SUPABASE credentials")
        return
        
    supabase = create_client(url, key)
    
    res = supabase.table("marketing_contacts").select("*").order("created_at", desc=False).execute()
    contacts = res.data or []
    
    seen_clients = {}
    seen_emails = {}
    to_delete = []
    
    for c in contacts:
        cid = c.get("client_id")
        email = c.get("email").strip().lower() if c.get("email") else None
        is_duplicate = False
        
        if cid:
            if cid in seen_clients: is_duplicate = True
            else: seen_clients[cid] = c
                
        if email:
            if email in seen_emails and not is_duplicate:
                existing = seen_emails[email]
                if existing.get("client_id") and not cid:
                    is_duplicate = True
                elif cid and not existing.get("client_id"):
                    to_delete.append(existing["id"])
                    if existing in seen_clients.values():
                        # remove existing from keep lists
                        pass 
                else:
                    is_duplicate = True
        
        if is_duplicate:
            to_delete.append(c["id"])
        else:
            if cid: seen_clients[cid] = c
            if email: seen_emails[email] = c

    if to_delete:
        print(f"Deleting {len(to_delete)} duplicate contacts...")
        # Break into chunks
        for i in range(0, len(to_delete), 50):
            chunk = to_delete[i:i+50]
            supabase.table("marketing_contacts").delete().in_("id", chunk).execute()
        print("Deduplication complete.")
    else:
        print("No duplicates found.")

if __name__ == "__main__":
    deduplicate()

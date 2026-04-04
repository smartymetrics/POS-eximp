import asyncio
from database import get_db

async def deduplicate_contacts():
    db = get_db()
    
    # 1. Fetch all marketing contacts
    res = db.table("marketing_contacts").select("*").order("created_at", desc=False).execute()
    contacts = res.data or []
    
    print(f"Total contacts before deduplication: {len(contacts)}")
    
    # Group by client_id (if they have one) or email
    seen_clients = {}
    seen_emails = {}
    
    to_delete = []
    to_keep = []
    
    for c in contacts:
        cid = c.get("client_id")
        email = c.get("email").strip().lower() if c.get("email") else None
        
        is_duplicate = False
        
        # If it has a client_id, check if we already saw it
        if cid:
            if cid in seen_clients:
                is_duplicate = True
            else:
                seen_clients[cid] = c
                
        # Also check by email
        if email:
            if email in seen_emails and not is_duplicate:
                # E.g. same email, different or no client_id
                # Usually we want to keep the one WITH a client_id
                existing = seen_emails[email]
                if existing.get("client_id") and not cid:
                    is_duplicate = True # keep existing
                elif cid and not existing.get("client_id"):
                    # We just found a better version.
                    to_delete.append(existing["id"])
                    if existing in to_keep:
                        to_keep.remove(existing)
                else:
                    is_duplicate = True
                    
        if is_duplicate:
            to_delete.append(c["id"])
        else:
            to_keep.append(c)
            if cid: seen_clients[cid] = c
            if email: seen_emails[email] = c

    print(f"Found {len(to_delete)} duplicates to delete.")
    
    if to_delete:
        # Delete in chunks
        for i in range(0, len(to_delete), 50):
            chunk = to_delete[i:i+50]
            db.table("marketing_contacts").delete().in_("id", chunk).execute()
        print("Duplicates deleted successfully.")
    
    print(f"Final safe contact count: {len(to_keep)}")

if __name__ == "__main__":
    asyncio.run(deduplicate_contacts())

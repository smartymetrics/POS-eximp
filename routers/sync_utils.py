from database import get_db

async def sync_historical_sales_data(admin_id: str, full_name: str, email: str):
    """
    Background task to link historical sales data to a new Admin account.
    Matches by Email (primary) or Full Name (secondary) against legacy 'sales_reps' table.
    Updates 'clients.assigned_rep_id' for all relevant leads.
    """
    db = get_db()
    
    # 1. Search for legacy rep match
    # Match by Email first
    legacy_rep = db.table("sales_reps").select("name").eq("email", email).execute()
    
    if not legacy_rep.data:
        # Fallback: Match by Name (case-insensitive)
        legacy_rep = db.table("sales_reps").select("name").ilike("name", full_name).execute()
        
    if not legacy_rep.data:
        print(f"Sync: No legacy rep found for '{full_name}' ({email})")
        return
        
    legacy_name = legacy_rep.data[0]["name"]
    print(f"Sync: Found legacy match! '{legacy_name}' maps to new Admin ID {admin_id}")
    
    # 2. Find all unique client IDs from invoices associated with this legacy name
    # We use invoices as the source of truth for who managed which client historically.
    client_ids_res = db.table("invoices").select("client_id").eq("sales_rep_name", legacy_name).execute()
    
    if not client_ids_res.data:
        print(f"Sync: Legacy rep '{legacy_name}' has no historical invoices.")
        return
        
    # Extract unique client IDs
    unique_client_ids = list(set(item["client_id"] for item in client_ids_res.data))
    print(f"Sync: Found {len(unique_client_ids)} historical clients to link.")
    
    # 3. Mass update clients table
    # Set assigned_rep_id for these clients if they aren't already assigned
    # (Actually, we'll overwrite to ensure the new official account takes over legacy records)
    for client_id in unique_client_ids:
        try:
            db.table("clients").update({"assigned_rep_id": admin_id}).eq("id", client_id).execute()
        except Exception as e:
            print(f"Sync: Error updating client {client_id}: {e}")
            
    print(f"Sync complete for {full_name}. Linked {len(unique_client_ids)} records.")

async def find_modern_admin_id(db, name: str = None, email: str = None):
    """
    Search for a modern Admin account matching a legacy name or email.
    """
    if email:
        res = db.table("admins").select("id").eq("email", email).execute()
        if res.data:
            return res.data[0]["id"]
            
    if name:
        res = db.table("admins").select("id").ilike("full_name", name.strip()).execute()
        if res.data:
            return res.data[0]["id"]
            
    return None

async def associate_client_with_rep(client_id: str, rep_name: str = None, rep_email: str = None, rep_id: str = None):
    """
    Ensures a client is assigned to the correct modern Admin account.
    If rep_id (Admin UUID) is explicitly provided, use it.
    Otherwise, search for a match in the Admin table based on legacy name/email.
    """
    db = get_db()
    
    admin_id = rep_id
    
    if not admin_id:
        admin_id = await find_modern_admin_id(db, name=rep_name, email=rep_email)
        
    if admin_id:
        try:
            db.table("clients").update({"assigned_rep_id": admin_id}).eq("id", client_id).execute()
            print(f"Sync: Successfully associated client {client_id} with Admin {admin_id}")
            return True
        except Exception as e:
            print(f"Sync: Error associating client {client_id}: {e}")
            
    return False

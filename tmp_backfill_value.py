from database import get_db

def sync_estimated_values():
    db = get_db()
    
    # 1. Fetch all invoices with their client IDs
    invoices = db.table("invoices").select("client_id, amount").neq("status", "voided").execute().data
    
    if not invoices:
         print("No invoices to sync.")
         return
    
    # 2. Aggregate amounts per client
    client_totals = {}
    for inv in invoices:
        cid = inv["client_id"]
        amt = float(inv.get("amount") or 0)
        client_totals[cid] = client_totals.get(cid, 0) + amt
        
    print(f"Aggregated values for {len(client_totals)} clients.")
    
    # 3. Update the clients table
    for cid, total in client_totals.items():
        db.table("clients").update({"estimated_value": total}).eq("id", cid).execute()
        
    print("Sync complete. All historical clients now have accurate estimated values in the CRM.")

if __name__ == "__main__":
    sync_estimated_values()

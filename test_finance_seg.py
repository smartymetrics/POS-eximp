import asyncio
import os
from database import get_db

async def test_financial_segmentation():
    print("--- [TEST] Financial Segmentation Diagnostic ---")
    db = get_db()
    
    # Fetch all active invoices joined with their clients
    invoices_res = db.table("invoices")\
        .select("amount, amount_paid, due_date, status, client_id, clients(email, full_name)")\
        .neq("status", "voided")\
        .execute()
    
    invoices = invoices_res.data or []
    print(f"Total active invoices found: {len(invoices)}")
    
    # Process financial State per client
    client_financials = {}
    from datetime import datetime
    today = datetime.utcnow().date().isoformat()
    
    for inv in invoices:
        client = inv.get("clients")
        if not client: continue
        email = client.get("email")
        if not email: continue
        
        email = email.lower().strip()
        
        if email not in client_financials:
            client_financials[email] = {
                "name": client["full_name"],
                "total_invoiced": 0,
                "total_paid": 0,
                "has_overdue": False,
                "outstanding": 0
            }
        
        amount = float(inv.get("amount") or 0)
        paid = float(inv.get("amount_paid") or 0)
        due_date = inv.get("due_date", "")
        
        client_financials[email]["total_invoiced"] += amount
        client_financials[email]["total_paid"] += paid
        
        # Consider overdue if paid less than amount AND due date is past
        if paid < amount and due_date and due_date < today:
            client_financials[email]["has_overdue"] = True
            
    # Group them up
    results = {
        "overdue": [],
        "outstanding": [],
        "paid_fully": []
    }
    
    for email, stats in client_financials.items():
        stats["outstanding"] = stats["total_invoiced"] - stats["total_paid"]
        
        if stats["has_overdue"]:
            results["overdue"].append(email)
        elif stats["outstanding"] > 0:
            results["outstanding"].append(email)
        elif stats["total_invoiced"] > 0:
            results["paid_fully"].append(email)
            
    print("\nSegmentation Summary:")
    print(f"🔴 Overdue Clients: {len(results['overdue'])}")
    print(f"🟡 Outstanding Clients (Not Overdue): {len(results['outstanding'])}")
    print(f"🟢 Paid Fully Clients: {len(results['paid_fully'])}")
    
    # Now check how many of these are ALREADY in the marketing_contacts table
    all_contacts_res = db.table("marketing_contacts").select("email").execute()
    marketing_emails = {c["email"].lower() for c in all_contacts_res.data}
    
    print(f"\nIntegration Status:")
    print(f"Total entries in marketing_contacts: {len(marketing_emails)}")
    financial_emails = set(client_financials.keys())
    missing_from_marketing = financial_emails - marketing_emails
    print(f"Clients missing from marketing_contacts: {len(missing_from_marketing)}")
    
    if missing_from_marketing:
        print(f"Sample missing: {list(missing_from_marketing)[:3]}")

if __name__ == "__main__":
    asyncio.run(test_financial_segmentation())

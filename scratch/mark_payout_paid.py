
from database import get_db, db_execute
import asyncio
from datetime import datetime, timezone

async def mark_paid():
    db = get_db()
    # Find the expenditure request
    res = await db_execute(lambda: db.table("expenditure_requests")
        .select("id, status, amount_gross, vendor_invoice_number, payment_type, vendor_id, requester_id")
        .eq("vendor_invoice_number", "EC-000021")
        .neq("status", "rejected")
        .execute()
    )
    
    if not res.data:
        print("No active expenditure request found for EC-000021.")
        return
    
    print(f"Found requests: {res.data}")
    
    # We want the one for 400,000 payment (which might have a different commission amount)
    # The user mentioned "This 400,000 pending" — likely refers to the client payment amount.
    # In the screenshot, instalment #2 is 400,000 and has commission "In Queue".
    
    # Let's look for a request with payment_type='instalment'
    reqs = [r for r in res.data if r.get("payment_type") == "instalment"]
    if not reqs:
        # Maybe it's not marked as instalment in the request?
        reqs = res.data
        
    for req in reqs:
        if req["status"] == "paid":
            print(f"Request {req['id']} is already marked as paid.")
            continue
            
        print(f"Marking request {req['id']} as paid...")
        
        # Update expenditure request
        await db_execute(lambda: db.table("expenditure_requests")
            .update({
                "status": "paid",
                "paid_at": datetime.now(timezone.utc).isoformat(),
                "notes": (req.get("notes") or "") + "\n[USER REQUEST] Marked as paid manually."
            })
            .eq("id", req["id"])
            .execute()
        )
        print(f"✓ Request {req['id']} updated to 'paid'.")

if __name__ == "__main__":
    asyncio.run(mark_paid())

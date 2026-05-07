
from database import get_db, db_execute
import asyncio
from datetime import datetime, timezone

async def void_payment():
    db = get_db()
    # Find the payment
    res = await db_execute(lambda: db.table("payments")
        .select("id, invoice_id, amount, reference, is_voided")
        .eq("amount", 40000)
        .eq("reference", "LEGACY-SYNC-EC-000021")
        .execute()
    )
    
    if not res.data:
        print("Payment not found.")
        return
    
    pmt = res.data[0]
    print(f"Found payment: {pmt}")
    
    if pmt.get("is_voided"):
        print("Payment is already voided.")
        return
    
    # Void the payment
    update_res = await db_execute(lambda: db.table("payments")
        .update({
            "is_voided": True,
            "voided_at": datetime.now(timezone.utc).isoformat(),
            "notes": "[USER REQUEST] Voided legacy sync payment of 40,000 for EC-000021"
        })
        .eq("id", pmt["id"])
        .execute()
    )
    
    if update_res.data:
        print(f"Successfully voided payment {pmt['id']}")
    else:
        print("Failed to void payment.")

if __name__ == "__main__":
    asyncio.run(void_payment())

import os
import asyncio
from database import get_db, db_execute
from decimal import Decimal

async def migrate():
    db = get_db()
    print("--- Starting Commission Rate Normalization ---")
    
    # 1. Fetch records with the legacy 9.5% rate (or where wht_amount is null)
    res = await db_execute(lambda: db.table("commission_earnings")\
        .select("*")\
        .eq("is_voided", False)\
        .execute())
    
    records = res.data or []
    updated_count = 0
    
    for r in records:
        # If rate is 9.5, it means it's a legacy record where WHT was already deducted
        # We need to set Gross=10, WHT=5 to make the math work for the new dashboard
        current_rate = float(r.get("commission_rate") or 0)
        
        if current_rate == 9.5 or (r.get("wht_amount") is None and current_rate > 0):
            # Calculate Gross from the Net
            # Net = 9.5% of Payment => Gross = 10% of Payment
            pay_amt = float(r.get("payment_amount") or 0)
            
            # Use 10% as standard gross if it was 9.5% net
            new_gross_rate = 10.0 if current_rate == 9.5 else current_rate
            new_wht_rate = 5.0
            
            gross_comm = round(pay_amt * new_gross_rate / 100, 2)
            wht_amt = round(gross_comm * new_wht_rate / 100, 2)
            net_comm = gross_comm - wht_amt
            
            # Update the record
            await db_execute(lambda: db.table("commission_earnings").update({
                "commission_rate": new_gross_rate,
                "gross_commission": gross_comm,
                "wht_amount": wht_amt,
                "net_commission": net_comm,
                "commission_amount": net_comm # Keep synced
            }).eq("id", r["id"]).execute())
            
            updated_count += 1
            print(f"Normalized ID {r['id']}: {current_rate}% -> {new_gross_rate}% (WHT: {wht_amt})")

    print(f"--- Migration Complete: {updated_count} records normalized ---")

if __name__ == "__main__":
    asyncio.run(migrate())

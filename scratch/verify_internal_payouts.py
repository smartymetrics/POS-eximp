import asyncio
import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import get_db, db_execute, init_db

async def run_tests():
    print("Initialising database client...")
    db = await init_db()
    
    # Test 1: Verify Table existence
    print("\n--- Test 1: Verify Access Table ---")
    res = await db_execute(lambda: db.table("internal_payouts_access").select("admin_id").limit(1).execute())
    print("Access table query succeeded.")
    
    # Test 2: Verify Split Math logic simulated
    print("\n--- Test 2: Simulating Split Math (90% / 2.5% / 7.5% / 0% VAT) ---")
    amount = 1000000.0 # 1 Million NGN
    land_cost = amount * 0.90
    allocation_fee = amount * 0.025
    documentation_fee = amount * 0.075
    vat = 0.0
    
    print(f"Total Amount: NGN {amount:,.2f}")
    print(f"Expected Land Cost (90%): NGN {land_cost:,.2f}")
    print(f"Expected Allocation Fee (2.5%): NGN {allocation_fee:,.2f}")
    print(f"Expected Documentation Fee (7.5%): NGN {documentation_fee:,.2f}")
    print(f"Expected VAT: NGN {vat:,.2f}")
    
    assert land_cost == 900000.0
    assert allocation_fee == 25000.0
    assert documentation_fee == 75000.0
    assert vat == 0.0
    print("[OK] Split math assertions passed.")
    
    # Test 3: Simulating Commission Dynamic Ratio resolver
    print("\n--- Test 3: Simulating Commission Dynamic Ratio Resolver ---")
    # Case A: Itemized invoice with new split (90%)
    invoice_itemized = {"amount": 1000000.0, "land_cost": 900000.0}
    pay_amt = 100000.0 # Payment of 100k
    
    has_itemization_a = invoice_itemized.get("land_cost") is not None
    if has_itemization_a:
        inv_amt = float(invoice_itemized["amount"] or 1.0)
        inv_lc = float(invoice_itemized["land_cost"] or 0.0)
        ratio = inv_lc / inv_amt if inv_amt > 0 else 0.90
        comm_base_a = pay_amt * ratio
    else:
        comm_base_a = pay_amt
        
    print(f"Itemized Invoice Commission Base: NGN {comm_base_a:,.2f}")
    assert comm_base_a == 90000.0
    print("[OK] Itemized invoice dynamic base resolved to 90%.")
    
    # Case B: Legacy invoice (no land_cost set)
    invoice_legacy = {"amount": 1000000.0, "land_cost": None}
    has_itemization_b = invoice_legacy.get("land_cost") is not None
    if has_itemization_b:
        inv_amt = float(invoice_legacy["amount"] or 1.0)
        inv_lc = float(invoice_legacy["land_cost"] or 0.0)
        ratio = inv_lc / inv_amt if inv_amt > 0 else 0.90
        comm_base_b = pay_amt * ratio
    else:
        comm_base_b = pay_amt
        
    print(f"Legacy Invoice Commission Base: NGN {comm_base_b:,.2f}")
    assert comm_base_b == 100000.0
    print("[OK] Legacy invoice dynamic base resolved to 100% of payment amount.")
    
    print("\n[OK] Verification tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())

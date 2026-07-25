import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, db_execute

async def main():
    db = get_db()
    
    print("=== PROPERTIES (PRODUCTS & SIZES) ===")
    prop_res = await db_execute(lambda: db.table("properties").select("*").execute())
    props = prop_res.data or []
    for p in props:
        print(f"ID: {p.get('id')} | Name: {p.get('name')} | Size: {p.get('plot_size_sqm')} sqm | Available: {p.get('available_plot_sizes')} | Starting Price: {p.get('starting_price')} | Price/sqm: {p.get('price_per_sqm')}")
        
    print("\n=== STAFF PROFILES (SALARIES) ===")
    try:
        staff_res = await db_execute(lambda: db.table("staff_profiles").select("id, full_name, base_salary").execute())
        staff = staff_res.data or []
        total_salary = 0.0
        for s in staff:
            val = float(s.get("base_salary") or 0.0)
            total_salary += val
            print(f"  - {s.get('full_name')}: NGN {val:,.2f}")
        print(f"Total Monthly Base Salary: NGN {total_salary:,.2f}")
    except Exception as e:
        print("Error getting staff profiles:", e)

    print("\n=== EXPENDITURE REQUESTS (OTHER OPERATIONAL EXPENSES) ===")
    try:
        exp_res = await db_execute(lambda: db.table("expenditure_requests").select("id, title, category, amount_gross, status").execute())
        exps = exp_res.data or []
        cat_sums = {}
        for e in exps:
            cat = e.get("category") or "Unknown"
            status = e.get("status") or "Unknown"
            if status.lower() == "paid":
                amt = float(e.get("amount_gross") or 0.0)
                cat_sums[cat] = cat_sums.get(cat, 0.0) + amt
        for cat, val in cat_sums.items():
            print(f"  - {cat} (Total Paid): NGN {val:,.2f}")
    except Exception as e:
        print("Error getting expenditure requests:", e)

    print("\n=== REVENUE / INVOICE ANALYSIS ===")
    try:
        inv_res = await db_execute(lambda: db.table("invoices").select("invoice_number, property_name, plot_size_sqm, amount, amount_paid, status, invoice_date").execute())
        invoices = inv_res.data or []
        print(f"Total Invoices: {len(invoices)}")
        # Print a few invoices
        for i in invoices[:10]:
            print(f"  - {i.get('invoice_number')} | {i.get('property_name')} | Size: {i.get('plot_size_sqm')} | Amount: {i.get('amount')} | Date: {i.get('invoice_date')}")
    except Exception as e:
        print("Error getting invoices:", e)

if __name__ == "__main__":
    asyncio.run(main())

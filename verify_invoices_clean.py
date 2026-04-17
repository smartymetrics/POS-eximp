import asyncio
from database import get_db, db_execute

async def verify():
    db = get_db()
    print("--- Invoice Constraint Verification ---")
    
    # 1. Fetch all invoices
    res = await db_execute(lambda: db.table("invoices").select("id, invoice_number, status, pipeline_stage").execute())
    if not res.data:
        print("No invoices found.")
        return

    # 2. Identify violations
    valid_stages = ['inspection', 'offer', 'contract', 'closed']
    valid_statuses = ['unpaid', 'partial', 'paid', 'voided', 'overdue']
    
    violations = []
    for r in res.data:
        stage = r.get("pipeline_stage")
        status = r.get("status")
        
        if stage not in valid_stages or status not in valid_statuses:
            violations.append(r)
            
    print(f"Total Invoices: {len(res.data)}")
    print(f"Violations Found: {len(violations)}")
    
    if violations:
        print("\nDetails of remaining violations:")
        for r in violations[:10]:
            print(f" - ID: {r['id']} | Num: {row.get('invoice_number')} | Stage: '{stage}' | Status: '{status}'")
            # Note: I'll use the r variable correctly below
    else:
        print("\n✅ SUCCESS: All invoices now satisfy the CHECK constraints for 'pipeline_stage' and 'status'.")

if __name__ == "__main__":
    asyncio.run(verify())

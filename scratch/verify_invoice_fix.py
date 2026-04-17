import asyncio
from database import get_db, db_execute

async def verify_constraints():
    db = get_db()
    print("Checking for rows violating CHECK constraints in 'invoices' table...")
    
    # Check pipeline_stage
    stages = await db_execute(lambda: db.table("invoices").select("id, invoice_number, status, pipeline_stage").execute())
    invalid_stages = [row for row in stages.data if row.get("pipeline_stage") not in ['inspection', 'offer', 'contract', 'closed']]
    
    if invalid_stages:
        print(f"❌ Found {len(invalid_stages)} rows with invalid pipeline_stage:")
        for row in invalid_stages[:5]:
            print(f"   - {row['invoice_number']}: stage='{row.get('pipeline_stage')}'")
    else:
        print("✅ No rows with invalid pipeline_stage found.")
        
    # Check status
    invalid_status = [row for row in stages.data if row.get("status") not in ['unpaid', 'partial', 'paid', 'voided', 'overdue']]
    if invalid_status:
        print(f"❌ Found {len(invalid_status)} rows with invalid status:")
        for row in invalid_status[:5]:
            print(f"   - {row['invoice_number']}: status='{row.get('status')}'")
    else:
        print("✅ No rows with invalid status found.")

    # Check for empty signatures if signature method is 'drawn'? No, that's not a constraint.
    
    # Check if there are any other check constraints we missed
    const_res = await db_execute(lambda: db.rpc("get_check_constraints", {"table_name": "invoices"}).execute())
    if const_res.data:
        print("\nExisting Check Constraints:")
        for c in const_res.data:
            print(f" - {c}")
    else:
        # Fallback: check schema for CHECK keywords if RPC fails
        print("\nRPC 'get_check_constraints' not found or returned no data.")

if __name__ == "__main__":
    asyncio.run(verify_constraints())

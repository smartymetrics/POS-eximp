"""
Targeted remediation for 4 affected invoices.
Updates descriptions with correct ClientAmt and fixes payments table.
"""

from database import get_db, db_execute
from datetime import datetime, timezone
import asyncio

db = get_db()

async def remediate_invoices():
    """Fix the 4 affected invoices with known client payment amounts."""
    
    print("\n" + "="*80)
    print("PAYOUT PORTAL BUG REMEDIATION - TARGETED FIX")
    print("="*80 + "\n")
    
    # Define the affected records with correct client amounts
    affected_records = [
        {
            "claim_id": "6bd051a2-9d26-4e34-bf25-35de9bde00cb",
            "invoice_id": "9cee7fce-5dbe-4b27-ac3e-0456b203c4f5",
            "invoice_number": "EC-000035",
            "commission_gross": 7500.00,
            "client_payment": 75000.00,
            "claim_type": "staff_commission",
            "status": "paid",
            "action": "fix"
        },
        {
            "claim_id": "f0ea39ae-e452-4095-8b98-766b6b0bf9ae",
            "invoice_id": "1ee906f6-f2c6-4994-b93f-bbaea4ede474",
            "invoice_number": "EC-000025",
            "commission_gross": 1500.00,
            "client_payment": None,
            "claim_type": "partner",
            "status": "rejected",
            "action": "void"
        },
        {
            "claim_id": "1ec97223-a15d-49d3-8f8b-618548d1fb20",
            "invoice_id": "1ee906f6-f2c6-4994-b93f-bbaea4ede474",
            "invoice_number": "EC-000025",
            "commission_gross": 15000.00,
            "client_payment": 150000.00,
            "claim_type": "staff_commission",
            "status": "paid",
            "action": "fix"
        },
        {
            "claim_id": "de35d814-583e-4acd-97d1-87e2c90404d4",
            "invoice_id": "78fb6477-7a08-477c-9aac-13d0bd56e799",
            "invoice_number": "EC-000021",
            "commission_gross": 40000.00,
            "client_payment": 400000.00,
            "claim_type": "partner",
            "status": "paid",
            "action": "verify"  # Already has correct amount in description
        }
    ]
    
    for record in affected_records:
        print(f"\n[{record['invoice_number']}] {record['claim_type'].upper()} - Commission ₦{record['commission_gross']:,.0f}")
        print("-" * 80)
        
        if record["action"] == "void":
            # REJECTED CLAIM: Void from payments table
            print(f"  ⚠️  REJECTED CLAIM - Voiding from payments...")
            
            # Find and void any payments on this invoice with CLAIM reference
            pmt_res = await db_execute(lambda: db.table("payments")
                .select("id, amount, reference")
                .eq("invoice_id", record["invoice_id"])
                .ilike("reference", "CLAIM-%")
                .eq("is_voided", False)
                .execute()
            )
            
            if pmt_res.data:
                for pmt in pmt_res.data:
                    await db_execute(lambda: db.table("payments")
                        .update({
                            "is_voided": True,
                            "voided_by": "remediation_script",
                            "voided_at": datetime.now(timezone.utc).isoformat(),
                            "notes": f"Voided - Rejected claim {record['claim_id'][:8]}"
                        })
                        .eq("id", pmt["id"])
                        .execute()
                    )
                    print(f"  ✓ Voided payment {pmt['id'][:8]} (was ₦{pmt['amount']:,.0f})")
            else:
                print(f"  ✓ No payments found to void (already clean)")
        
        elif record["action"] in ["fix", "verify"]:
            # Update description with correct ClientAmt
            new_description = f"Portal submission via {record['claim_type']}\nClientAmt: {record['client_payment']}\nCommission: {record['commission_gross']}"
            
            await db_execute(lambda: db.table("expenditure_requests")
                .update({"description": new_description})
                .eq("id", record["claim_id"])
                .execute()
            )
            print(f"  ✓ Updated description with ClientAmt: ₦{record['client_payment']:,.0f}")
            
            # Now check if payment was created with WRONG amount (commission instead of client payment)
            pmt_res = await db_execute(lambda: db.table("payments")
                .select("id, amount, reference, payment_method")
                .eq("invoice_id", record["invoice_id"])
                .ilike("reference", "CLAIM-%")
                .eq("is_voided", False)
                .execute()
            )
            
            if pmt_res.data:
                for pmt in pmt_res.data:
                    if float(pmt["amount"]) == record["commission_gross"]:
                        # WRONG AMOUNT - was recorded as commission, not client payment
                        print(f"  ⚠️  FOUND WRONG PAYMENT: ₦{pmt['amount']:,.0f} (was commission)")
                        print(f"      Correcting to client payment: ₦{record['client_payment']:,.0f}")
                        
                        await db_execute(lambda: db.table("payments")
                            .update({"amount": record["client_payment"]})
                            .eq("id", pmt["id"])
                            .execute()
                        )
                        print(f"  ✓ Payment corrected")
                    else:
                        print(f"  ✓ Payment exists with correct amount: ₦{pmt['amount']:,.0f}")
            else:
                print(f"  ℹ️  No payment found yet (will be created on next verification)")
    
    print("\n" + "="*80)
    print("REMEDIATION COMPLETE")
    print("="*80 + "\n")
    
    print("SUMMARY:")
    print("  • EC-000035: Description updated, payment corrected if needed")
    print("  • EC-000025 (Partner): Rejected claim voided from payments")
    print("  • EC-000025 (Staff): Description updated, payment corrected if needed")
    print("  • EC-000021: Description updated, verified as correct")
    print("\n")


if __name__ == "__main__":
    asyncio.run(remediate_invoices())

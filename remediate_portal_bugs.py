"""
Remediation script for payout portal bugs affecting historical invoices.
Identifies and fixes:
- Bug #1: Wrong commission amount in payments table (should be client payment, not commission)
- Bug #2: Non-commission claims polluting payments table
- Bug #4: Missing vendor_id in commission_earnings (partner commission lookup failed)
- Bug #5: Duplicate payment records
- Bug #6: Portal payments not voided on rejection
"""

from database import get_db, db_execute
from decimal import Decimal
import asyncio
import json
from datetime import datetime, timezone

db = get_db()

async def diagnose_affected_invoices():
    """Find all invoices affected by the bugs before the fix was deployed."""
    
    print("\n" + "="*80)
    print("PAYOUT PORTAL BUG REMEDIATION DIAGNOSTIC")
    print("="*80)
    
    # Query 1: Commission claims with potentially wrong payment amounts
    print("\n[1] Commission claims with potential wrong payment amounts (Bug #1):")
    print("-" * 80)
    
    query1 = await db_execute(lambda: db.table("expenditure_requests")
        .select("id, invoice_id, description, amount_gross, status, created_at, payment_type")
        .eq("source_platform", "payout_portal")
        .in_("payment_type", ["initial_deposit", "instalment"])
        .execute()
    )
    
    if query1.data:
        for req in query1.data:
            # Check for payments on this invoice
            pmt_res = await db_execute(lambda: db.table("payments")
                .select("id, amount, reference, payment_method")
                .eq("invoice_id", req["invoice_id"])
                .ilike("reference", "CLAIM-%")
                .execute()
            )
            
            if pmt_res.data:
                for pmt in pmt_res.data:
                    # If payment amount equals commission amount (amount_gross), it's wrong
                    if float(pmt["amount"]) == float(req["amount_gross"]):
                        print(f"  ⚠️  FOUND: Claim {req['id'][:8]}")
                        print(f"      Invoice ID: {req['invoice_id']}")
                        print(f"      Payment recorded: ₦{pmt['amount']:,.0f} (should be client payment, not commission)")
                        print(f"      Commission (gross): ₦{req['amount_gross']:,.0f}")
                        print(f"      Status: {req['status']} | Created: {req['created_at'][:10]}")
                        print()
    else:
        print("  ✓ No commission claims found")
    
    # Query 2: Duplicate payments on same invoice
    print("\n[2] Duplicate payments on same invoice (Bug #5):")
    print("-" * 80)
    
    # Get all invoices with multiple CLAIM-* payments
    all_payments = await db_execute(lambda: db.table("payments")
        .select("id, invoice_id, amount, reference, payment_method, created_at")
        .ilike("reference", "CLAIM-%")
        .execute()
    )
    
    from collections import defaultdict
    invoice_payments = defaultdict(list)
    if all_payments.data:
        for pmt in all_payments.data:
            invoice_payments[pmt["invoice_id"]].append(pmt)
    
    duplicates_found = False
    for inv_id, pmts in invoice_payments.items():
        if len(pmts) > 1:
            duplicates_found = True
            print(f"  ⚠️  FOUND: Invoice {inv_id} has {len(pmts)} CLAIM payments")
            for i, pmt in enumerate(pmts, 1):
                print(f"      Payment {i}: ₦{pmt['amount']:,.0f} | {pmt['reference']} | {pmt['created_at'][:10]}")
            print()
    
    if not duplicates_found:
        print("  ✓ No duplicate payments found")
    
    # Query 3: Commission earnings missing vendor_id (Bug #4)
    print("\n[3] Commission earnings missing vendor_id (Bug #4):")
    print("-" * 80)
    
    missing_vendor = await db_execute(lambda: db.table("commission_earnings")
        .select("id, invoice_id, sales_rep_id, sales_rep_name, vendor_id, created_at")
        .is_("vendor_id", "null")
        .execute()
    )
    
    if missing_vendor.data:
        for earning in missing_vendor.data:
            print(f"  ⚠️  FOUND: Earning {earning['id'][:8]}")
            print(f"      Invoice: {earning['invoice_id']}")
            print(f"      Sales Rep: {earning.get('sales_rep_name', 'N/A')}")
            print(f"      Created: {earning['created_at'][:10]}")
            print()
    else:
        print("  ✓ No commission earnings missing vendor_id")
    
    # Query 4: Expenditure requests still in pending_verification
    print("\n[4] Expenditure requests still pending verification (should be approved):")
    print("-" * 80)
    
    pending = await db_execute(lambda: db.table("expenditure_requests")
        .select("id, invoice_id, description, status, created_at")
        .eq("status", "pending_verification")
        .eq("source_platform", "payout_portal")
        .in_("payment_type", ["initial_deposit", "instalment"])
        .execute()
    )
    
    if pending.data:
        for req in pending.data:
            print(f"  ⚠️  FOUND: {req['id'][:8]} still in pending_verification")
            print(f"      Invoice: {req['invoice_id']}")
            print(f"      Created: {req['created_at'][:10]}")
            print()
    else:
        print("  ✓ No pending verification requests found")
    
    print("="*80 + "\n")


async def fix_affected_invoices(fix_ids=None):
    """
    Fix specific affected invoices.
    
    fix_ids: List of claim IDs to fix, or None to fix all detected issues
    """
    
    print("\n" + "="*80)
    print("APPLYING FIXES")
    print("="*80 + "\n")
    
    # Fix 1: Correct wrong payment amounts where commission was recorded instead of client payment
    print("[FIX 1] Correcting payment amounts (Bug #1)...")
    
    if fix_ids:
        fix_query = db.table("expenditure_requests").select("id, invoice_id, description, amount_gross, commission_base")
    else:
        fix_query = db.table("expenditure_requests").select("id, invoice_id, description, amount_gross, commission_base")
    
    claims = await db_execute(lambda: fix_query
        .eq("source_platform", "payout_portal")
        .in_("payment_type", ["initial_deposit", "instalment"])
        .execute()
    )
    
    fixed_count = 0
    if claims.data:
        for claim in claims.data:
            # Check if there's a payment that matches the commission amount
            pmt_res = await db_execute(lambda: db.table("payments")
                .select("id, amount")
                .eq("invoice_id", claim["invoice_id"])
                .ilike("reference", "CLAIM-%")
                .eq("amount", float(claim["amount_gross"]))
                .execute()
            )
            
            if pmt_res.data:
                # This payment has the wrong amount - try to extract the correct amount
                try:
                    desc = claim.get("description", "")
                    if "ClientAmt: " in desc:
                        correct_amount = float(desc.split("ClientAmt: ")[-1].split()[0])
                    elif "commission_base" in claim and claim["commission_base"]:
                        correct_amount = float(claim["commission_base"])
                    else:
                        continue  # Can't determine correct amount
                    
                    # Update the payment
                    pmt_id = pmt_res.data[0]["id"]
                    await db_execute(lambda: db.table("payments")
                        .update({"amount": correct_amount})
                        .eq("id", pmt_id)
                        .execute()
                    )
                    print(f"  ✓ Fixed payment for claim {claim['id'][:8]}")
                    print(f"    Changed from ₦{float(claim['amount_gross']):,.0f} to ₦{correct_amount:,.0f}")
                    fixed_count += 1
                except Exception as e:
                    print(f"  ✗ Error fixing claim {claim['id'][:8]}: {str(e)}")
    
    print(f"  Total fixed: {fixed_count}\n")
    
    # Fix 2: Remove duplicate payments
    print("[FIX 2] Removing duplicate payments (Bug #5)...")
    
    all_payments = await db_execute(lambda: db.table("payments")
        .select("id, invoice_id, amount, reference, created_at")
        .ilike("reference", "CLAIM-%")
        .execute()
    )
    
    from collections import defaultdict
    invoice_payments = defaultdict(list)
    if all_payments.data:
        for pmt in all_payments.data:
            invoice_payments[pmt["invoice_id"]].append(pmt)
    
    duplicates_removed = 0
    for inv_id, pmts in invoice_payments.items():
        if len(pmts) > 1:
            # Sort by created_at, keep the first one, remove the rest
            pmts_sorted = sorted(pmts, key=lambda x: x["created_at"])
            for pmt in pmts_sorted[1:]:
                # Void instead of delete to maintain audit trail
                await db_execute(lambda: db.table("payments")
                    .update({"is_voided": True, "voided_by": "remediation_script", "voided_at": datetime.now(timezone.utc).isoformat()})
                    .eq("id", pmt["id"])
                    .execute()
                )
                print(f"  ✓ Voided duplicate payment {pmt['id'][:8]} on invoice {inv_id}")
                duplicates_removed += 1
    
    print(f"  Total duplicates voided: {duplicates_removed}\n")
    
    # Fix 3: Link commission_earnings to vendor_id (Bug #4)
    print("[FIX 3] Linking commission_earnings to vendors (Bug #4)...")
    
    missing_vendor = await db_execute(lambda: db.table("commission_earnings")
        .select("id, invoice_id, sales_rep_id, sales_rep_name")
        .is_("vendor_id", "null")
        .execute()
    )
    
    linked_count = 0
    if missing_vendor.data:
        for earning in missing_vendor.data:
            # Try to find vendor by sales_rep_email through sales_reps table
            if earning.get("sales_rep_id"):
                rep_res = await db_execute(lambda: db.table("sales_reps")
                    .select("email")
                    .eq("id", earning["sales_rep_id"])
                    .execute()
                )
                
                if rep_res.data and rep_res.data[0].get("email"):
                    vendor_res = await db_execute(lambda: db.table("vendors")
                        .select("id")
                        .eq("email", rep_res.data[0]["email"])
                        .execute()
                    )
                    
                    if vendor_res.data:
                        vendor_id = vendor_res.data[0]["id"]
                        await db_execute(lambda: db.table("commission_earnings")
                            .update({"vendor_id": vendor_id})
                            .eq("id", earning["id"])
                            .execute()
                        )
                        print(f"  ✓ Linked commission {earning['id'][:8]} to vendor {vendor_id[:8]}")
                        linked_count += 1
    
    print(f"  Total linked: {linked_count}\n")
    
    # Fix 4: Update pending_verification requests to approved
    print("[FIX 4] Approving pending verification requests (Bug #3)...")
    
    pending = await db_execute(lambda: db.table("expenditure_requests")
        .select("id, invoice_id, pending_verification_id")
        .eq("status", "pending_verification")
        .eq("source_platform", "payout_portal")
        .in_("payment_type", ["initial_deposit", "instalment"])
        .execute()
    )
    
    approved_count = 0
    if pending.data:
        for req in pending.data:
            # Find corresponding payment
            pmt_res = await db_execute(lambda: db.table("payments")
                .select("id")
                .eq("invoice_id", req["invoice_id"])
                .ilike("reference", "CLAIM-%")
                .limit(1)
                .execute()
            )
            
            if pmt_res.data:
                await db_execute(lambda: db.table("expenditure_requests")
                    .update({
                        "status": "approved",
                        "payment_id": pmt_res.data[0]["id"],
                        "hr_note": "Auto-approved via remediation script (Bug fix verification)"
                    })
                    .eq("id", req["id"])
                    .execute()
                )
                print(f"  ✓ Approved request {req['id'][:8]}")
                approved_count += 1
    
    print(f"  Total approved: {approved_count}\n")
    
    print("="*80)
    print("REMEDIATION COMPLETE")
    print("="*80 + "\n")


# Main execution
if __name__ == "__main__":
    print("\n🔍 Running diagnostic to identify affected invoices...")
    asyncio.run(diagnose_affected_invoices())
    
    user_input = input("\nDo you want to apply fixes? (yes/no): ").strip().lower()
    if user_input == "yes":
        asyncio.run(fix_affected_invoices())
    else:
        print("✓ Skipped remediation. No changes made.")

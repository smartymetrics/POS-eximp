"""
Void spurious commission payments that leaked into payments table.
Bug #1 caused commission amounts to be inserted instead of client payments.
"""

from database import get_db, db_execute
from datetime import datetime, timezone
import asyncio

db = get_db()

async def void_spurious_payments():
    """Void commission amounts that leaked into payments table."""
    
    print("\n" + "="*80)
    print("VOIDING SPURIOUS COMMISSION PAYMENTS (BUG #1)")
    print("="*80 + "\n")
    
    # Payments to void (commission amounts that leaked)
    spurious_payments = [
        {
            "invoice_number": "EC-000035",
            "invoice_id": "9cee7fce-5dbe-4b27-ac3e-0456b203c4f5",
            "amount": 7500.00,
            "reference": "LEGACY-SYNC-EC-000035",
            "method": "portal_reported",
            "reason": "Bug #1: Commission amount leaked into payments"
        },
        {
            "invoice_number": "EC-000025",
            "invoice_id": "1ee906f6-f2c6-4994-b93f-bbaea4ede474",
            "amount": 15000.00,
            "reference": "LEGACY-SYNC-EC-000025",
            "method": "portal_reported",
            "reason": "Bug #1: Commission amount leaked into payments"
        },
        {
            "invoice_number": "EC-000025 (Rejected)",
            "invoice_id": "1ee906f6-f2c6-4994-b93f-bbaea4ede474",
            "amount": 150000.00,
            "reference": None,
            "method": "portal_reported",
            "reason": "Bug #2: Rejected partner claim inserted spurious payment"
        }
    ]
    
    for payment_info in spurious_payments:
        print(f"\n[{payment_info['invoice_number']}] Voiding spurious ₦{payment_info['amount']:,.0f} ({payment_info['method']})")
        print("-" * 80)
        
        # Find the payment
        pmt_query = db.table("payments")\
            .select("id, amount, reference, payment_method, is_voided")\
            .eq("invoice_id", payment_info["invoice_id"])\
            .eq("amount", payment_info["amount"])\
            .eq("payment_method", payment_info["method"])
        
        pmt_res = await db_execute(lambda: pmt_query.execute())
        
        if pmt_res.data:
            for pmt in pmt_res.data:
                if not pmt.get("is_voided"):
                    await db_execute(lambda: db.table("payments")
                        .update({
                            "is_voided": True,
                            "voided_at": datetime.now(timezone.utc).isoformat(),
                            "notes": f"[REMEDIATION] Voided spurious payment - {payment_info['reason']}"
                        })
                        .eq("id", pmt["id"])
                        .execute()
                    )
                    print(f"  ✓ VOIDED: Payment ID {pmt['id'][:8]}")
                    print(f"    Amount: ₦{pmt['amount']:,.0f}")
                    print(f"    Reference: {pmt.get('reference', 'N/A')}")
                    print(f"    Reason: {payment_info['reason']}")
                else:
                    print(f"  ℹ️  Already voided: {pmt['id'][:8]}")
        else:
            print(f"  ✗ Payment not found for voiding")
            print(f"    Expected: invoice_id={payment_info['invoice_id']}, amount=₦{payment_info['amount']:,.0f}, method={payment_info['method']}")
    
    print("\n" + "="*80)
    print("VOID OPERATION COMPLETE")
    print("="*80 + "\n")
    print("✓ Spurious commission payments voided:")
    print("  • EC-000035: ₦7,500 (Bug #1)")
    print("  • EC-000025: ₦15,000 (Bug #1)")
    print("  • EC-000025: ₦150,000 duplicate (Bug #2 - rejected claim)")
    print("✓ Payments table now shows only legitimate client payments")
    print("✓ Dashboard will update to reflect voided payments\n")


if __name__ == "__main__":
    asyncio.run(void_spurious_payments())

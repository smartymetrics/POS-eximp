"""
test_signature_rejection.py
Tests signature rejection endpoints:
- POST /api/contracts/{invoice_id}/reject-client-signature
- POST /api/contracts/{invoice_id}/witness/{witness_id}/reject
Run: .\.venv\Scripts\python.exe scratch/test_signature_rejection.py
"""
import asyncio, sys, os
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from routers.auth import verify_token
from database import get_db, db_execute

# Override verify_token dynamically
mock_user = {"sub": "f8406ab8-00f6-45a2-a735-f7019e659238", "role": "admin"}
app.dependency_overrides[verify_token] = lambda: mock_user

client = TestClient(app)

async def test_suite():
    db = get_db()
    print("=" * 60)
    print("STARTING SIGNATURE REJECTION INTEGRATION TESTS")
    print("=" * 60)

    # Clean up any leftover test data
    print("Running pre-test cleanup...")
    test_client_emails = ["test-reject-client@example.com", "smartymetric+client@gmail.com", "smartymetric@gmail.com"]
    for test_client_email in test_client_emails:
        c_res = await db_execute(lambda: db.table("clients").select("id").eq("email", test_client_email).execute())
        for row in (c_res.data or []):
            c_id = row["id"]
            # Find related invoices
            inv_res = await db_execute(lambda: db.table("invoices").select("id").eq("client_id", c_id).execute())
            for inv in (inv_res.data or []):
                # Delete sessions and witness signatures
                sess_res = await db_execute(lambda: db.table("contract_signing_sessions").select("id").eq("invoice_id", inv["id"]).execute())
                for s in (sess_res.data or []):
                    await db_execute(lambda: db.table("witness_signatures").delete().eq("session_id", s["id"]).execute())
                    await db_execute(lambda: db.table("contract_signing_sessions").delete().eq("id", s["id"]).execute())
                await db_execute(lambda: db.table("activity_log").delete().eq("invoice_id", inv["id"]).execute())
                await db_execute(lambda: db.table("void_log").delete().eq("invoice_id", inv["id"]).execute())
                await db_execute(lambda: db.table("invoices").delete().eq("id", inv["id"]).execute())
    print("  [OK] Pre-test cleanup completed.")

    # 1. Create a mock client
    print("\nSTEP 1: Creating mock client...")
    test_client_email = "smartymetric@gmail.com"
    c_res = await db_execute(lambda: db.table("clients").select("id").eq("email", test_client_email).execute())
    if c_res.data:
        client_id = c_res.data[0]["id"]
        created_client = False
        print(f"  [OK] Found existing client: {client_id}")
    else:
        client_res = await db_execute(lambda: db.table("clients").insert({
            "full_name": "Reject Test Client",
            "email": test_client_email,
            "phone": "08012345678",
            "client_type": "client"
        }).execute())
        client_id = client_res.data[0]["id"]
        created_client = True
        print(f"  [OK] Client created: {client_id}")

    # 2. Create a mock invoice with client signature already present
    print("\nSTEP 2: Creating mock invoice...")
    invoice_res = await db_execute(lambda: db.table("invoices").insert({
        "invoice_number": "TEST-REJ-INV-001",
        "client_id": client_id,
        "amount": 15000000.00,
        "property_name": "Palm Grove Estate",
        "due_date": "2026-12-31",
        "pipeline_stage": "paid",
        "contract_signature_url": "https://supabase/signatures/test_sig.png",
        "contract_signature_method": "drawn",
        "contract_signed_at": "2026-06-29T10:00:00Z"
    }).execute())
    invoice_id = invoice_res.data[0]["id"]
    print(f"  [OK] Invoice created: {invoice_id}")

    # 3. Create active signing session
    print("\nSTEP 3: Creating mock signing session...")
    session_res = await db_execute(lambda: db.table("contract_signing_sessions").insert({
        "invoice_id": invoice_id,
        "token": "test_rejection_token_999",
        "status": "completed",
        "expires_at": "2026-12-31T23:59:59Z"
    }).execute())
    session_id = session_res.data[0]["id"]
    print(f"  [OK] Session created: {session_id}")

    # 4. Create mock witness signature
    print("\nSTEP 4: Creating mock witness signature...")
    witness_res = await db_execute(lambda: db.table("witness_signatures").insert({
        "session_id": session_id,
        "witness_number": 1,
        "full_name": "Test Witness One",
        "witness_email": "smartymetric@gmail.com",
        "signature_base64": "https://supabase/signatures/witness_sig.png",
        "signature_method": "drawn",
        "address": "123 Test Street",
        "occupation": "Engineer",
        "acknowledgement": True
    }).execute())
    witness_id = witness_res.data[0]["id"]
    print(f"  [OK] Witness signature created: {witness_id}")

    # 5. Test Witness Rejection Endpoint
    print("\nSTEP 5: Testing Witness Rejection API...")
    rej_reason = "Witness signature is blurred."
    response = client.post(
        f"/api/contracts/{invoice_id}/witness/{witness_id}/reject",
        json={"reason": rej_reason}
    )
    print(f"  Response status: {response.status_code}")
    print(f"  Response body: {response.json()}")
    assert response.status_code == 200, "Witness signature rejection failed"
    
    # Verify DB changes for Witness
    witness_check = await db_execute(lambda: db.table("witness_signatures").select("*").eq("id", witness_id).execute())
    assert not witness_check.data, "Witness signature was not deleted from database!"
    print("  [PASS] Witness signature successfully deleted.")

    session_check = await db_execute(lambda: db.table("contract_signing_sessions").select("status, expires_at").eq("id", session_id).execute())
    assert session_check.data[0]["status"] == "pending", f"Session status should be reverted to pending, but got {session_check.data[0]['status']}."
    
    # Assert session duration is extended to ~48 hours
    expires_at = isoparse(session_check.data[0]["expires_at"])
    now = datetime.now(timezone.utc)
    diff = expires_at - now
    assert timedelta(hours=47) < diff < timedelta(hours=49), f"Session expiration should be extended by 48 hours, but got diff of {diff}."
    print("  [PASS] Signing session status correctly reverted to pending and expiration extended by 48 hours.")

    # 6. Test Client Rejection Endpoint
    print("\nSTEP 6: Testing Client Rejection API...")
    rej_reason = "Client signature doesn't match client identification card."
    # Make session completed again to test status reversion
    await db_execute(lambda: db.table("contract_signing_sessions").update({"status": "completed"}).eq("id", session_id).execute())

    response = client.post(
        f"/api/contracts/{invoice_id}/reject-client-signature",
        json={"reason": rej_reason}
    )
    print(f"  Response status: {response.status_code}")
    print(f"  Response body: {response.json()}")
    assert response.status_code == 200, "Client signature rejection failed"

    # Verify DB changes for Client
    invoice_check = await db_execute(lambda: db.table("invoices").select("*").eq("id", invoice_id).execute())
    inv = invoice_check.data[0]
    assert inv["contract_signature_url"] is None, "Client signature URL was not cleared!"
    assert inv["contract_signed_at"] is None, "Client signature signed timestamp was not cleared!"
    print("  [PASS] Client signature columns successfully cleared from invoices table.")

    session_check = await db_execute(lambda: db.table("contract_signing_sessions").select("status, expires_at").eq("id", session_id).execute())
    assert session_check.data[0]["status"] == "pending", f"Session status should be reverted to pending on client rejection, but got {session_check.data[0]['status']}."
    
    # Assert session duration is extended to ~48 hours
    expires_at = isoparse(session_check.data[0]["expires_at"])
    now = datetime.now(timezone.utc)
    diff = expires_at - now
    assert timedelta(hours=47) < diff < timedelta(hours=49), f"Session expiration should be extended by 48 hours, but got diff of {diff}."
    print("  [PASS] Signing session status correctly reverted to pending and expiration extended by 48 hours.")

    # Clean up test data
    print("\nSTEP 7: Performing post-test cleanup...")
    await db_execute(lambda: db.table("activity_log").delete().eq("invoice_id", invoice_id).execute())
    await db_execute(lambda: db.table("void_log").delete().eq("invoice_id", invoice_id).execute())
    await db_execute(lambda: db.table("contract_signing_sessions").delete().eq("id", session_id).execute())
    await db_execute(lambda: db.table("invoices").delete().eq("id", invoice_id).execute())
    if created_client:
        await db_execute(lambda: db.table("activity_log").delete().eq("client_id", client_id).execute())
        await db_execute(lambda: db.table("marketing_contacts").delete().eq("client_id", client_id).execute())
        await db_execute(lambda: db.table("clients").delete().eq("id", client_id).execute())
    print("  [OK] Cleaned up test data.")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_suite())

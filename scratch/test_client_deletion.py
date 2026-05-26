"""
test_client_deletion.py
Tests the DELETE /api/clients/{client_id} endpoint.
Uses FastAPI TestClient to verify role enforcement, invoice protection, and DB cleanup.
Run: .\.venv\Scripts\python.exe scratch/test_client_deletion.py
"""
import asyncio, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from routers.auth import verify_token
from database import get_db, db_execute

# We will use this to override verify_token dynamically
mock_user = {"sub": "f8406ab8-00f6-45a2-a735-f7019e659238", "role": "super_admin"}
app.dependency_overrides[verify_token] = lambda: mock_user

client = TestClient(app)

async def test_suite():
    db = get_db()
    print("=" * 60)
    print("STARTING CLIENT DELETION INTEGRATION TESTS")
    print("=" * 60)

    # Pre-test cleanup for idempotency
    print("Running pre-test cleanup...")
    c_res = await db_execute(lambda: db.table("clients").select("id").eq("email", "test-delete-contact@example.com").execute())
    for row in (c_res.data or []):
        c_id = row["id"]
        await db_execute(lambda: db.table("activity_log").delete().eq("client_id", c_id).execute())
        await db_execute(lambda: db.table("email_logs").delete().eq("client_id", c_id).execute())
        await db_execute(lambda: db.table("invoices").delete().eq("client_id", c_id).execute())
    
    await db_execute(lambda: db.table("marketing_contacts").delete().eq("email", "test-delete-contact@example.com").execute())
    await db_execute(lambda: db.table("clients").delete().eq("email", "test-delete-contact@example.com").execute())
    print("  [OK] Pre-test cleanup completed.")

    # 1. Create a mock client
    print("\nSTEP 1: Creating mock client in database...")
    mock_client_data = {
        "full_name": "Test Delete Contact",
        "email": "test-delete-contact@example.com",
        "phone": "09998887776",
        "client_type": "lead",
        "pipeline_stage": "interest"
    }
    insert_res = await db_execute(lambda: db.table("clients").insert(mock_client_data).execute())
    if not insert_res.data:
        print("  [FAIL] Failed to create mock client.")
        return
    client_id = insert_res.data[0]["id"]
    print(f"  [OK] Mock Client Created. ID: {client_id}")

    # 2. Add some related entries to test cleanup logic
    print("\nSTEP 2: Inserting related entries in dependent tables...")
    # Add activity_log
    await db_execute(lambda: db.table("activity_log").insert({
        "event_type": "note_added",
        "description": "Mock note to test cleanup",
        "client_id": client_id,
        "performed_by": "f8406ab8-00f6-45a2-a735-f7019e659238"
    }).execute())
    # Add marketing_contact
    await db_execute(lambda: db.table("marketing_contacts").insert({
        "client_id": client_id,
        "first_name": "Test",
        "last_name": "Delete",
        "email": "test-delete-contact@example.com",
        "phone": "09998887776",
        "contact_type": "lead"
    }).execute())
    print("  [OK] Inserted activity_log and marketing_contacts entries.")

    # 3. Try to delete as a non-super_admin (e.g. staff role)
    print("\nSTEP 3: Testing non-super_admin role rejection...")
    mock_user["role"] = "staff"  # Change role to standard staff
    response = client.delete(f"/api/clients/{client_id}")
    print(f"  Response status: {response.status_code}")
    print(f"  Response body: {response.json()}")
    if response.status_code == 403:
        print("  [PASS] Non-super_admin was correctly rejected with 403!")
    else:
        print("  [FAIL] Endpoint did not reject non-super_admin with 403!")

    # Restore super_admin role
    mock_user["role"] = "super_admin"

    # 4. Create a mock invoice to test invoice protection
    print("\nSTEP 4: Testing invoice protection (blocking deletion)...")
    mock_invoice_data = {
        "invoice_number": "TEST-DEL-INV-001",
        "client_id": client_id,
        "amount": 5000000.0,
        "due_date": "2026-12-31",
        "pipeline_stage": "interest"
    }
    inv_res = await db_execute(lambda: db.table("invoices").insert(mock_invoice_data).execute())
    invoice_id = inv_res.data[0]["id"]
    print(f"  [OK] Mock Invoice Created. ID: {invoice_id}")

    # Now attempt deletion as super_admin
    response = client.delete(f"/api/clients/{client_id}")
    print(f"  Response status: {response.status_code}")
    print(f"  Response body: {response.json()}")
    if response.status_code == 400:
        print("  [PASS] Deletion was correctly blocked due to attached invoice!")
    else:
        print("  [FAIL] Deletion was NOT blocked when invoice was attached!")

    # 5. Delete/cleanup the mock invoice to test successful deletion
    print("\nSTEP 5: Removing attached invoice and attempting deletion...")
    await db_execute(lambda: db.table("invoices").delete().eq("id", invoice_id).execute())
    print("  [OK] Mock Invoice deleted.")

    # Now attempt deletion again as super_admin
    response = client.delete(f"/api/clients/{client_id}")
    print(f"  Response status: {response.status_code}")
    print(f"  Response body: {response.json()}")
    if response.status_code == 200:
        print("  [PASS] Deletion succeeded with 200!")
    else:
        print(f"  [FAIL] Deletion failed with status {response.status_code}!")

    # 6. Verify database cleanup
    print("\nSTEP 6: Verifying database cleanup...")
    client_check = await db_execute(lambda: db.table("clients").select("id").eq("id", client_id).execute())
    if not client_check.data:
        print("  [PASS] Client was successfully deleted from clients table!")
    else:
        print("  [FAIL] Client still exists in clients table!")

    log_check = await db_execute(lambda: db.table("activity_log").select("id").eq("client_id", client_id).execute())
    if not log_check.data:
        print("  [PASS] Client activity log was successfully cleared!")
    else:
        print("  [FAIL] Client activity log still exists!")

    mkt_check = await db_execute(lambda: db.table("marketing_contacts").select("client_id").eq("email", "test-delete-contact@example.com").execute())
    if mkt_check.data and mkt_check.data[0].get("client_id") is None:
        print("  [PASS] Marketing contact was successfully unlinked (client_id set to NULL)!")
    else:
        print("  [FAIL] Marketing contact was not unlinked!")

    # Clean up marketing contact
    await db_execute(lambda: db.table("marketing_contacts").delete().eq("email", "test-delete-contact@example.com").execute())
    print("  [OK] Mock marketing contact cleaned up.")

    print("\n" + "=" * 60)
    print("INTEGRATION TESTS COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_suite())

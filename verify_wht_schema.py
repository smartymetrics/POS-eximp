from database import get_db

def verify_schema():
    db = get_db()
    try:
        # Check if columns exist by selecting them
        db.table("expenditure_requests").select("is_wht_remitted").limit(1).execute()
        print("✅ Column 'is_wht_remitted' exists.")
    except Exception as e:
        print(f"❌ Column 'is_wht_remitted' MISSING: {e}")

    try:
        # Check if partially_paid is allowed by trying to find one or just checking metadata if possible
        # We'll just try to select one
        res = db.table("expenditure_requests").select("id").eq("status", "partially_paid").limit(1).execute()
        print("✅ Status 'partially_paid' query succeeded.")
    except Exception as e:
        print(f"❌ Status 'partially_paid' query FAILED: {e}")

if __name__ == "__main__":
    verify_schema()

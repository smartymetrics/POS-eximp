from database import get_db

db = get_db()
try:
    db.storage.create_bucket("documents")
    print("Bucket created")
except Exception as e:
    print(f"Error creating bucket (might already exist): {e}")

try:
    # Try updating bucket to public
    db.storage.update_bucket("documents", {"public": True})
    print("Bucket made public")
except Exception as e:
    print(f"Error updating bucket: {e}")

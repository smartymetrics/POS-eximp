from database import get_db
import sys

def migrate():
    try:
        db = get_db()
        print("🚀 Checking Database for Multi-Role Support...")
        
        # Check columns
        res = db.table("admins").select("*").limit(1).execute()
        if not res.data:
            print("No admins found to check.")
            return
            
        admin = res.data[0]
        has_primary = "primary_role" in admin
        
        if not has_primary:
            print("\n⚠️  DATABASE UPDATE REQUIRED!")
            print("Please run this SQL in your Supabase SQL Editor to enable multiple roles:")
            print("-" * 50)
            print("ALTER TABLE admins DROP CONSTRAINT IF EXISTS admins_role_check;")
            print("ALTER TABLE admins ALTER COLUMN role TYPE VARCHAR(255);")
            print("ALTER TABLE admins ADD COLUMN IF NOT EXISTS primary_role VARCHAR(50) DEFAULT 'staff';")
            print("UPDATE admins SET primary_role = role WHERE primary_role IS NULL;")
            print("-" * 50)
        else:
            print("✅ Database already has primary_role column.")
            
    except Exception as e:
        print(f"❌ Error during check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()

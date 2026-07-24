import os
from database import supabase
from postgrest.exceptions import APIError

def run_migration():
    print("Running migration to add is_internal column...")
    try:
        # Check if column exists
        try:
            supabase.table('job_requisitions').select('is_internal').limit(1).execute()
            print("Column 'is_internal' already exists.")
            return
        except APIError:
            pass
        
        # This is a hacky way since we don't have exec_sql usually.
        # We'll try to add it via a dummy RPC if it exists, or just tell the user.
        print("Column missing. Please run this SQL in Supabase Editor:")
        print("ALTER TABLE job_requisitions ADD COLUMN is_internal BOOLEAN DEFAULT false;")
        
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    run_migration()

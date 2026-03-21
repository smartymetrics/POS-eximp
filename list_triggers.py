import asyncio
import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def list_all_triggers():
    db = get_db()
    
    # We can try to use a raw select on pg_trigger via RPC if we have one
    # If not, let's try a clever trick: 
    # Query a table that exists and might give us info
    
    print("Checking triggers via PostgREST introspection...")
    try:
        # A common way to get schema info is via RPC or the root endpoint
        # But we'll try to just guess the trigger name or find it via a clever query
        
        # Let's try to query a system table if allowed
        sql = """
        SELECT trigger_name, event_manipulation, event_object_table, action_statement
        FROM information_schema.triggers
        WHERE event_object_table = 'invoices'
        """
        # We can't run raw SQL. 
        
        # Let's try to see if 'unmatched_reps' trigger exists by error message exploration
        # Or better: check the traceback in detail.
    except Exception as e:
        print(f"Error: {e}")

    # Let's try to see what's in the 'invoices' table currently
    res = db.table("invoices").select("id, sales_rep_name").limit(5).execute()
    print(f"Current Invoices in DB: {res.data}")

if __name__ == "__main__":
    asyncio.run(list_all_triggers())

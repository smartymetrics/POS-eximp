import asyncio
import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

async def inspect_functions():
    db = get_db()
    
    # We'll try to use the 'rpc' to find function info if possible, 
    # but since we can't run raw SQL, we'll try to find a system-info RPC.
    # If not, let's just guess the most likely triggers.
    
    print("Inspecting functions via POSTGREST...")
    try:
        # Check if we can describe the schema
        # Usually, GET with Prefer: params=single-object on a table can give info
        # But we'll try a different approach.
        pass
    except Exception as e:
        print(f"Error: {e}")

    # Let's try to see if there's any trigger on 'clients' specifically
    # since we got "Client Upsert requires a WHERE clause"
    print("\nAttempting client insert with ALL fields...")
    # This might trigger the error and give more clues
    try:
        db.table("clients").insert({"full_name": "Test", "email": "test@error.com"}).execute()
    except Exception as e:
        print(f"Captured Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_functions())

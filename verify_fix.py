import asyncio
from database import supabase
from decimal import Decimal
from fastapi.encoders import jsonable_encoder

async def verify():
    print("Testing Decimal serialization with jsonable_encoder...")
    test_data = {
        "name": "Test Rep Serializer",
        "email": "test_rep_serializer@example.com",
        "phone": "0000000000",
        "commission_rate": Decimal("7.5")
    }
    
    # This mimics what the router now does
    encoded_data = jsonable_encoder(test_data)
    print(f"Encoded Data: {encoded_data}")
    
    try:
        res = supabase.table("sales_reps").insert(encoded_data).execute()
        print(" ✅ Success: Data inserted successfully!")
        
        # Cleanup
        if res.data:
            supabase.table("sales_reps").delete().eq("id", res.data[0]["id"]).execute()
            print(" ✅ Success: Test data cleaned up.")
    except Exception as e:
        print(f" ❌ Failure: {e}")

if __name__ == "__main__":
    asyncio.run(verify())

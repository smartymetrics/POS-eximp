import asyncio
import os
import sys
import jwt
from datetime import datetime, timedelta

# Ensure we can import database
sys.path.append(os.getcwd())

async def main():
    from database import get_db, db_execute
    db = get_db()
    
    SECRET_KEY = os.getenv("JWT_SECRET", "eximp-cloves-secret-key-change-in-production")
    ALGORITHM = "HS256"
    
    # Let's find an active admin with admin or super_admin role
    res = await db_execute(lambda: db.table("admins").select("*").eq("is_active", True).execute())
    if not res.data:
        print("No active admins found")
        return
        
    for admin in res.data:
        role = admin.get("role") or ""
        primary_role = admin.get("primary_role") or ""
        email = admin.get("email") or ""
        name = admin.get("full_name") or ""
        
        # Check if they have admin privileges
        if "admin" in role.lower() or "super" in role.lower() or "admin" in primary_role.lower():
            # Generate token
            token_data = {
                "sub": admin["id"], 
                "email": email, 
                "role": role, 
                "primary_role": primary_role,
                "staff_type": "full"
            }
            token = jwt.encode(
                {**token_data, "exp": datetime.utcnow() + timedelta(hours=24)},
                SECRET_KEY,
                algorithm=ALGORITHM
            )
            print(f"FOUND_ADMIN|{name}|{email}|{role}|{token}")
            return
            
    # If no admin-level role found, generate token for the first active user anyway but override role to super_admin for testing
    admin = res.data[0]
    token_data = {
        "sub": admin["id"], 
        "email": admin["email"], 
        "role": "super_admin", 
        "primary_role": "super_admin",
        "staff_type": "full"
    }
    token = jwt.encode(
        {**token_data, "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    print(f"GENERATED_TEST_ADMIN|{admin['full_name']}|{admin['email']}|super_admin|{token}")

if __name__ == "__main__":
    asyncio.run(main())

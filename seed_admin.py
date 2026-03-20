"""
Run this script once to create your first admin account.
Usage: python seed_admin.py
"""
import bcrypt
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def create_admin(full_name: str, email: str, password: str, role: str = "admin"):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    result = supabase.table("admins").insert({
        "full_name": full_name,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "is_active": True
    }).execute()
    print(f"✅ Admin created: {email}")
    return result.data[0]


if __name__ == "__main__":
    print("═" * 50)
    print("  Eximp & Cloves — Admin Account Setup")
    print("═" * 50)

    name = input("Full name: ").strip()
    email = input("Email address: ").strip()
    password = input("Password: ").strip()

    try:
        admin = create_admin(name, email, password, role="admin")
        print(f"\n✅ Success! You can now log in at /login")
        print(f"   Email: {email}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

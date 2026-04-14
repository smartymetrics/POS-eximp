import requests
import json
import os

# Configuration
API_URL = "http://localhost:8000" # Change if the app is on a different port
ADMIN_EMAIL = "admin@example.com" # Use an existing admin email
ADMIN_PASS = "admin123"           # Use the existing admin password

# Prototype Users Data
USERS = [
    {
        "full_name": "Femi Adeyemi",
        "email": "f.adeyemi@eximps-cloves.com",
        "password": "hr2026",
        "role": "hr_admin,admin",
        "primary_role": "hr",
        "department": "HR"
    },
    {
        "full_name": "Amaka Okonkwo",
        "email": "a.okonkwo@eximps-cloves.com",
        "password": "lm2026",
        "role": "line_manager,staff",
        "primary_role": "hr",
        "department": "Operations"
    },
    {
        "full_name": "Chidi Eze",
        "email": "c.eze@eximps-cloves.com",
        "password": "ce2026",
        "role": "staff",
        "primary_role": "dashboard"
    },
    {
        "full_name": "Tunde Olawale",
        "email": "t.olawale@eximps-cloves.com",
        "password": "to2026",
        "role": "staff",
        "primary_role": "dashboard"
    },
    {
        "full_name": "Ebele Nwosu",
        "email": "e.nwosu@eximps-cloves.com",
        "password": "en2026",
        "role": "staff",
        "primary_role": "dashboard"
    }
]

def seed():
    print("--- HR Data Seeding Started ---")
    
    # 1. Login to get Admin Token
    print(f"Logging in as {ADMIN_EMAIL}...")
    try:
        login_res = requests.post(f"{API_URL}/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASS
        })
        if not login_res.ok:
            print(f"Login failed: {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Run Migration (Optional if already run)
        print("Triggering SQL migration...")
        mig_res = requests.post(f"{API_URL}/api/hr/migrate", headers=headers)
        print(f"Migration: {mig_res.json().get('message')}")
        
        # 3. Create Users
        for user in USERS:
            print(f"Creating user: {user['full_name']}...")
            reg_res = requests.post(f"{API_URL}/auth/register", json=user, headers=headers)
            if reg_res.ok:
                print(f"Successfully created {user['email']}")
            else:
                print(f"Failed to create {user['email']}: {reg_res.text}")
                
    except Exception as e:
        print(f"Connection error: {e}. Is the server running at {API_URL}?")

    print("--- Seeding Finished ---")

if __name__ == "__main__":
    seed()

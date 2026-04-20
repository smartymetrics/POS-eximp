import os
import sys
import csv
import re
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

CSV_PATH = "Sales Lead - Form Responses 2.csv"

# FINAL MAPPING USING NEWLY CREATED ADMIN IDs
REPS_MAP = {
    "miracle": "32dd1711-cfaa-4c2a-bb6d-637a513b4d47",
    "omole": "32dd1711-cfaa-4c2a-bb6d-637a513b4d47",
    "onofa": "32dd1711-cfaa-4c2a-bb6d-637a513b4d47",
    "olamilekan": "8d4193b6-f1d1-40bd-a9eb-063f2a5afc9f",
    "ogunyoye": "8d4193b6-f1d1-40bd-a9eb-063f2a5afc9f",
    "florence": "0e65758a-11df-4e36-a10f-80e8717ee7ba",
    "akanni": "0e65758a-11df-4e36-a10f-80e8717ee7ba",
    "olamide": "9170e704-cae9-4e7a-97c7-f131a90c010a",
    "dosumu": "9170e704-cae9-4e7a-97c7-f131a90c010a",
    "martha": "096f6004-de15-4680-ba8f-a9cbbf260846",
    "samuel": "89eb524a-7b33-404e-8fd9-c3e268d616aa",
    "fadodun": "89eb524a-7b33-404e-8fd9-c3e268d616aa",
    "bolu": "260f4fa9-d5be-4be3-845e-e79f17d9eafb",
    "tife": "260f4fa9-d5be-4be3-845e-e79f17d9eafb"
}

def sanitize_phone(phone):
    if not phone: return ""
    phone = str(phone).strip()
    phone = re.sub(r'[^\d+]', '', phone)
    if phone.startswith('0'):
        phone = '+234' + phone[1:]
    elif phone.startswith('234'):
        phone = '+' + phone
    elif phone and not phone.startswith('+'):
        phone = '+234' + phone
    return phone

def find_rep_id(name):
    if not name: return None
    q = name.lower().strip()
    for key, val in REPS_MAP.items():
        if key in q:
            return val
    return None

def reassign_leads(commit=False):
    print(f"Starting FINAL reassignment (Commit: {commit})...")
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    count_updated = 0
    count_skipped = 0
    errors = []

    for i, row in enumerate(rows):
        phone_keys = [k for k in row.keys() if "Phone" in k]
        agent_keys = [k for k in row.keys() if "Agent" in k]
        
        phone = sanitize_phone(row.get(phone_keys[0], "") if phone_keys else "")
        agent_name = row.get(agent_keys[0], "").strip() if agent_keys else ""
        
        rep_id = find_rep_id(agent_name)
        
        if not phone or not rep_id:
            count_skipped += 1
            continue

        placeholder_email = f"lead_{phone.replace('+', '')}@temp-eximps.com"

        # 1. Update Client (assigned_rep_id AND added_by for visibility)
        if commit:
            try:
                # Update assigned_rep_id column if it exists, and added_by for strict RBAC
                res = supabase.table("clients").update({
                    "assigned_rep_id": rep_id,
                    "added_by": rep_id
                }).eq("email", placeholder_email).execute()
                
                # 2. Update Activity Logs for this client
                c_res = supabase.table("clients").select("id").eq("email", placeholder_email).execute()
                if c_res.data:
                    cid = c_res.data[0]["id"]
                    # Update metadata AND performed_by
                    supabase.table("activity_log").update({
                        "performed_by": rep_id
                    }).eq("client_id", cid).eq("event_type", "sales_lead_log").execute()
                    
                count_updated += 1
            except Exception as e:
                errors.append(f"Row {i+1} ({agent_name}): {e}")
        else:
            count_updated += 1

        if (i+1) % 20 == 0:
            print(f"Processed {i+1}/{len(rows)}...")

    print(f"\n--- FINAL REASSIGNMENT SUMMARY ---")
    print(f"Total leads reassigned: {count_updated}")
    print(f"Total skipped: {count_skipped}")
    if errors:
        print(f"Errors encountered: {len(errors)}")
        for e in errors[:5]:
            print(f"  - {e}")

if __name__ == "__main__":
    is_commit = "--commit" in sys.argv
    reassign_leads(commit=is_commit)

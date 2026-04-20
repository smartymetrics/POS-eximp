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

# HARD CODED MAPPING FROM RESEARCH
REPS_MAP = {
    "miracle": "d2e29cdd-efcf-42a7-824a-e91e1d7d0b35",
    "omole": "d2e29cdd-efcf-42a7-824a-e91e1d7d0b35",
    "olamilekan": "4656cde0-c0a4-4085-91a6-143815cfc380",
    "florence": "82974c14-d526-4de1-9699-04258bea2341",
    "olamide": "2248f4e7-a307-4336-a626-35a8616634e8",
    "martha": "50ac60d6-3e7a-4788-860f-12eb4fe3d6f8",
    "samuel": "278cb502-9aa9-41c5-aebd-00f06b007f90",
    "bolu": "a2c7825e-dd93-4b29-82f1-02be37ba5dc4",
    "usein": "751e7875-2996-4f2b-af44-1e83fba3b626",
    "oluwaseun": "751e7875-2996-4f2b-af44-1e83fba3b626"
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
    print(f"Starting reassignment (Commit: {commit})...")
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    count_updated = 0
    count_skipped = 0

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

        # 1. Update Client
        if commit:
            res = supabase.table("clients").update({"assigned_rep_id": rep_id}).eq("email", placeholder_email).execute()
            if not res.data:
                # Try by phone if email match failed (fallback)
                supabase.table("clients").update({"assigned_rep_id": rep_id}).eq("phone", phone).execute()
        
        # 2. Update Activity Logs for this client
        if commit:
            # We fetch client ID first to be safe
            c_res = supabase.table("clients").select("id").eq("phone", phone).execute()
            if c_res.data:
                cid = c_res.data[0]["id"]
                # Update metadata to include rep name for clarity
                logs = supabase.table("activity_log").select("id, metadata").eq("client_id", cid).eq("event_type", "sales_lead_log").execute()
                for log in logs.data:
                    meta = log["metadata"] or {}
                    meta["assigned_to_rep_name"] = agent_name
                    supabase.table("activity_log").update({"metadata": meta}).eq("id", log["id"]).execute()

        count_updated += 1
        if (i+1) % 20 == 0:
            print(f"Processed {i+1}/{len(rows)}...")

    print(f"\n--- REASSIGNMENT SUMMARY ---")
    print(f"Total leads reassigned: {count_updated}")
    print(f"Total skipped (no mapping): {count_skipped}")

if __name__ == "__main__":
    is_commit = "--commit" in sys.argv
    reassign_leads(commit=is_commit)

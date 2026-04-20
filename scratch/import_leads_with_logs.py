import asyncio
import os
import sys
import csv
import re
from datetime import datetime

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from database import get_db, db_execute

# CSV Configuration
CSV_PATH = "Sales Lead - Form Responses 2.csv"

def sanitize_phone(phone):
    if not phone: return ""
    phone = str(phone).strip()
    phone = re.sub(r'[^\d+]', '', phone)
    if phone.startswith('0'):
        phone = '+234' + phone[1:]
    elif phone.startswith('234'):
        phone = '+' + phone
    elif not phone.startswith('+'):
        phone = '+234' + phone
    return phone

def parse_budget(budget_str):
    if not budget_str: return 0
    s = str(budget_str).lower().strip()
    try:
        if 'million' in s:
            val_match = re.findall(r"[-+]?\d*\.\d+|\d+", s)
            if val_match:
                val = float(val_match[0])
                return int(val * 1000000)
        num_match = re.search(r'[\d.]+', s.replace(',', ''))
        if num_match:
            return int(float(num_match.group()))
    except:
        pass
    return 0

admin_map = {}

async def load_admins():
    db = get_db()
    res = await db_execute(lambda: db.table("admins").select("id, full_name").eq("is_active", True).execute())
    if res.data:
        for admin in res.data:
            admin_map[admin['full_name'].lower().strip()] = admin['id']
    print(f"Loaded {len(admin_map)} active admins.")

def find_admin_by_fuzzy_name(name, fallback_id):
    if not name: return fallback_id
    query = name.lower().strip()
    
    # Exact match in names
    if query in admin_map:
        return admin_map[query]
    
    # Partial match
    for full_name, admin_id in admin_map.items():
        if query in full_name or full_name in query:
            return admin_id
            
    # First name match
    first_name = query.split()[0]
    for full_name, admin_id in admin_map.items():
        if first_name in full_name:
            return admin_id
            
    return fallback_id

async def import_data(commit=False):
    db = get_db()
    await load_admins()
    
    # Fallback info
    fallback_id = list(admin_map.values())[0] if admin_map else None

    # Load CSV
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print(f"Starting import of {len(rows)} rows (Commit: {commit})", flush=True)
    
    count_new = 0
    count_existing = 0
    count_logs = 0

    for i, row in enumerate(rows):
        try:
            # 1. Sanitize Data
            raw_name = row.get("Lead Name") or "Unknown Lead"
            full_name = raw_name.strip()
            
            # The column name from my earlier view_file was "  Phone Number  "
            phone_key = [k for k in row.keys() if "Phone" in k][0]
            phone = sanitize_phone(row.get(phone_key, ""))
            
            budget_key = [k for k in row.keys() if "Budget" in k][0]
            budget = parse_budget(row.get(budget_key, "0"))
            
            timestamp = row.get("Timestamp", datetime.now().isoformat())
            agent_key = [k for k in row.keys() if "Agent" in k][0]
            agent_name = row.get(agent_key, "").strip()
            
            admin_id = find_admin_by_fuzzy_name(agent_name, fallback_id)
            
            if not full_name or not phone:
                continue

            # 2. Upsert Client
            client_id = None
            client_res = await db_execute(lambda: db.table("clients").select("id").eq("phone", phone).execute())
            
            if client_res.data:
                client_id = client_res.data[0]["id"]
                count_existing += 1
                # Optional: Update existing lead's budget if higher?
            else:
                count_new += 1
                if commit:
                    new_client = {
                        "full_name": full_name,
                        "phone": phone,
                        "email": f"lead_{phone.replace('+', '')}@temp-eximps.com", # Constraint workaround
                        "added_by": admin_id,
                        "estimated_value": budget,
                        "state": row.get("  Location of Lead  ", "").strip(),
                        "created_at": timestamp
                    }
                    res = await db_execute(lambda: db.table("clients").insert(new_client).execute())
                    if res.data:
                        client_id = res.data[0]["id"]
                else:
                    client_id = "DRY_RUN_ID"

            # 3. Create Activity Log
            if client_id:
                # Merge relevant info into description/metadata
                remarks = row.get("Remarks", "No remarks")
                activity_desc = f"Imported Data: {remarks}"
                
                metadata = {
                    "estate_name": row.get("Estate Name", ""),
                    "estate_location": row.get("Estate Location", ""),
                    "interaction_type": row.get("Interaction Type  ", ""),
                    "inspection_status": row.get("Inspection Status  ", ""),
                    "lead_sentiment": row.get("Lead Sentiment  ", ""),
                    "key_barrier": row.get("Key Barrier  ", ""),
                    "action_required": row.get("Action Required ", ""),
                    "source": "bulk_import_apr_2026"
                }

                log_entry = {
                    "event_type": "sales_lead_log",
                    "description": activity_desc,
                    "client_id": client_id,
                    "performed_by": admin_id,
                    "metadata": metadata,
                    "created_at": timestamp
                }
                
                if commit:
                    await db_execute(lambda: db.table("activity_log").insert(log_entry).execute())
                
                count_logs += 1
                
        except Exception as e:
            print(f"Error on row {i+1}: {e}")

        if (i + 1) % 20 == 0:
            print(f"Processed {i+1}/{len(rows)} leads...", flush=True)

    print(f"--- FINAL SUMMARY ---")
    print(f"New Leads Found: {count_new}")
    print(f"Existing Leads Linked: {count_existing}")
    print(f"Total Activity Logs Processed: {count_logs}")

if __name__ == "__main__":
    is_commit = "--commit" in sys.argv
    asyncio.run(import_data(commit=is_commit))

import os
import sys
import csv
import re

sys.path.append(os.getcwd())
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

CSV_PATH = "Sales Lead - Form Responses 2.csv"

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

def parse_budget(budget_str):
    if not budget_str: return 0
    s = str(budget_str).lower().strip()
    try:
        if 'million' in s:
            val_match = re.findall(r"[-+\d.]+", s)
            if val_match:
                return int(float(val_match[0]) * 1000000)
        num_match = re.search(r'[\d.]+', s.replace(',', ''))
        if num_match:
            return int(float(num_match.group()))
    except:
        pass
    return 0

# Build admin map
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

admin_map = {}
res = supabase.table("admins").select("id, full_name, role").eq("is_active", True).execute()
for admin in res.data:
    admin_map[admin['full_name'].lower().strip()] = {"id": admin['id'], "name": admin['full_name'], "role": admin.get('role')}

def find_admin(name):
    if not name: return None, "UNMATCHED"
    q = name.lower().strip()
    if q in admin_map: return admin_map[q]['id'], admin_map[q]['name']
    for full_name, info in admin_map.items():
        if q in full_name or full_name in q:
            return info['id'], info['name']
    first = q.split()[0]
    for full_name, info in admin_map.items():
        if first in full_name:
            return info['id'], info['name']
    return None, "UNMATCHED"

print("\n=== DRY RUN PREVIEW: First 10 rows ===\n")
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"CSV columns: {list(rows[0].keys())[:8]}")
print()

for i, row in enumerate(rows[:10]):
    phone_keys = [k for k in row.keys() if "Phone" in k]
    budget_keys = [k for k in row.keys() if "Budget" in k]
    agent_keys = [k for k in row.keys() if "Agent" in k]
    
    name = (row.get("Lead Name") or "").strip()
    phone = sanitize_phone(row.get(phone_keys[0], "") if phone_keys else "")
    budget = parse_budget(row.get(budget_keys[0], "") if budget_keys else "")
    agent_raw = row.get(agent_keys[0], "").strip() if agent_keys else ""
    admin_id, admin_name = find_admin(agent_raw)
    
    print(f"Row {i+1}: {name!r:<30} | Phone: {phone:<16} | Budget: {budget:>12,} | Agent: {agent_raw!r:<20} -> {admin_name!r}")

print(f"\n\nTotal admins available for matching:")
for name, info in admin_map.items():
    print(f"  - {info['name']!r} (role: {info['role']})")

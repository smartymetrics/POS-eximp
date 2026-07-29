import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from database import get_db

db = get_db()

res = db.table("expenditure_requests").select("id, title, category, receipt_url, proforma_url, status, created_at").order("created_at", desc=True).limit(25).execute()

print(f"Fetched {len(res.data or [])} expenditure requests:")
for r in (res.data or []):
    print(f"ID: {r['id']} | Status: {r['status']} | Created: {r.get('created_at')}")
    print(f"  Title: {r.get('title')}")
    print(f"  Receipt URL: {r.get('receipt_url')}")
    print(f"  Proforma URL: {r.get('proforma_url')}")
    print("-" * 60)

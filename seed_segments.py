import os
import sys
# Add current directory to path so it can find database.py
sys.path.append(os.getcwd())

from database import get_db

def seed():
    try:
        db = get_db()
        # List of segments from PRD 6 §4.3
        segs = [
            {"name": "All Subscribed Contacts", "description": "Everyone who has not opted out.", "segment_type": "dynamic", "filter_rules": [{"field": "is_subscribed", "op": "eq", "val": True}]},
            {"name": "All Clients", "description": "Contacts marked as client type.", "segment_type": "dynamic", "filter_rules": [{"field": "contact_type", "op": "eq", "val": "client"}]},
            {"name": "All Leads", "description": "Contacts marked as lead type.", "segment_type": "dynamic", "filter_rules": [{"field": "contact_type", "op": "eq", "val": "lead"}]},
            {"name": "Clients with Outstanding Balance", "description": "Clients who still owe money on active invoices.", "segment_type": "dynamic", "filter_rules": [{"field": "financial_status", "op": "eq", "val": "outstanding"}]},
            {"name": "Hot Leads", "description": "High engagement score (70+).", "segment_type": "dynamic", "filter_rules": [{"field": "engagement_score", "op": "gte", "val": 70}]},
            {"name": "Dormant Contacts", "description": "Low engagement score (below 10).", "segment_type": "dynamic", "filter_rules": [{"field": "engagement_score", "op": "lt", "val": 10}]},
            {"name": "Recent Subscribers", "description": "Joined in the last 30 days.", "segment_type": "dynamic", "filter_rules": [{"field": "created_at", "op": "in_last", "val": 30}]}
        ]
        
        for s in segs:
            # Check if already exists by name to avoid duplicates
            res = db.table("marketing_segments").select("id").eq("name", s["name"]).execute()
            if not res.data:
                db.table("marketing_segments").insert(s).execute()
                print(f"Added: {s['name']}")
            else:
                print(f"Skipped (already exists): {s['name']}")
        print("--- Seeding Complete ---")
    except Exception as e:
        print(f"Seeding error: {e}")

if __name__ == "__main__":
    seed()

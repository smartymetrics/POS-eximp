"""
Run once to seed the 7 default marketing segments.
Usage: python scripts/seed_marketing_segments.py
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db

DEFAULT_SEGMENTS = [
    {
        "name": "All Subscribed Contacts",
        "description": "Every contact who is currently subscribed to marketing emails.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "is_subscribed", "op": "eq", "val": True}]
    },
    {
        "name": "All Clients",
        "description": "Contacts identified as ECOMS clients.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "contact_type", "op": "eq", "val": "client"}, {"field": "is_subscribed", "op": "eq", "val": True}]
    },
    {
        "name": "All Leads",
        "description": "Contacts who are leads but not yet clients.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "contact_type", "op": "eq", "val": "lead"}, {"field": "is_subscribed", "op": "eq", "val": True}]
    },
    {
        "name": "Hot Leads",
        "description": "Leads with engagement score of 70 or higher.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "contact_type", "op": "eq", "val": "lead"}, {"field": "engagement_score", "op": "gte", "val": 70}, {"field": "is_subscribed", "op": "eq", "val": True}]
    },
    {
        "name": "Dormant Contacts",
        "description": "Subscribed contacts who have not interacted in over 90 days.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "is_subscribed", "op": "eq", "val": True}, {"field": "engagement_score", "op": "lt", "val": 10}, {"field": "last_interaction_at", "op": "older_than", "val": 90}]
    },
    {
        "name": "Recent Subscribers",
        "description": "Contacts who joined in the last 30 days.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "is_subscribed", "op": "eq", "val": True}, {"field": "created_at", "op": "in_last", "val": 30}]
    },
    {
        "name": "Clients with Outstanding Balance",
        "description": "Clients who have unpaid invoices. Uses financial segment resolver.",
        "segment_type": "dynamic",
        "filter_rules": [{"field": "financial_status", "op": "eq", "val": "financial_outstanding"}]
    }
]

def seed():
    db = get_db()
    for seg in DEFAULT_SEGMENTS:
        # Check if it already exists by name
        existing = db.table("marketing_segments").select("id").eq("name", seg["name"]).execute()
        if existing.data:
            print(f"  SKIP — already exists: {seg['name']}")
            continue
        result = db.table("marketing_segments").insert(seg).execute()
        if result.data:
            print(f"  CREATED: {seg['name']}")
        else:
            print(f"  FAILED: {seg['name']}")

if __name__ == "__main__":
    print("Seeding default marketing segments...")
    seed()
    print("Done.")

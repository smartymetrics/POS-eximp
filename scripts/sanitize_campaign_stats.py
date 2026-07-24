"""
purge_suppressed_recipients.py
==============================
Deletes all campaign recipient rows associated with suppressed contacts (temp-eximps.com / placeholder.com)
to completely clean up the historical analytics, and runs recalculate_stats.
"""

import sys, os
sys.path.insert(0, r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh")
os.chdir(r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh")

from database import get_db
from datetime import datetime

db = get_db()
SUPPRESSED_DOMAINS = ["temp-eximps.com", "placeholder.com"]

print("=" * 60)
print("PURGING SUPPRESSED RECIPIENT HISTORICAL RECORDS")
print("=" * 60)

# 1. Fetch suppressed contacts
print("\n[1] Finding suppressed contacts...")
supp_contacts = []
for domain in SUPPRESSED_DOMAINS:
    res = db.table("marketing_contacts").select("id, email").ilike("email", f"%{domain}%").execute()
    supp_contacts.extend(res.data or [])

suppressed_ids = list({c["id"] for c in supp_contacts})
print(f"    Found {len(suppressed_ids)} suppressed contacts.")

# 2. Purge campaign recipients
print("\n[2] Purging campaign recipient history for suppressed contacts...")
total_purged = 0
if suppressed_ids:
    # Batch delete
    batch_size = 100
    for i in range(0, len(suppressed_ids), batch_size):
        batch_ids = suppressed_ids[i:i+batch_size]
        
        # Get count first
        count_res = db.table("campaign_recipients").select("id", count="exact").in_("contact_id", batch_ids).execute()
        count = count_res.count or 0
        
        # Delete
        db.table("campaign_recipients").delete().in_("contact_id", batch_ids).execute()
        total_purged += count

print(f"    Deleted {total_purged} recipient logs belonging to suppressed contacts.")

# 3. Recalculate campaign aggregates
print("\n[3] Recalculating campaign stats...")
camps_res = db.table("email_campaigns").select("id, name").not_.eq("status", "draft").execute()
campaigns = camps_res.data or []

for camp in campaigns:
    camp_id = camp["id"]
    name = (camp["name"] or "")[:40]
    
    # Recalculate
    delivered_res = db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", camp_id).eq("status", "delivered").execute()
    actual_delivered = delivered_res.count or 0
    
    delivered_a_res = db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", camp_id).eq("status", "delivered").eq("variant", "A").execute()
    variant_a = delivered_a_res.count or 0
    
    delivered_b_res = db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", camp_id).eq("status", "delivered").eq("variant", "B").execute()
    variant_b = delivered_b_res.count or 0
    
    # We should also count total recipient records remaining for this campaign to set total_recipients
    total_recs_res = db.table("campaign_recipients").select("id", count="exact").eq("campaign_id", camp_id).execute()
    total_remaining = total_recs_res.count or 0
    
    # Update aggregates
    db.table("email_campaigns").update({
        "total_sent": actual_delivered,
        "total_recipients": total_remaining,
        "variant_a_sent": variant_a,
        "variant_b_sent": variant_b,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", camp_id).execute()
    
    print(f"    Recalculated {name} (ID: {camp_id}): total={total_remaining}, delivered={actual_delivered}, A={variant_a}, B={variant_b}")

print("\n" + "=" * 60)
print("DATABASE SANITIZATION COMPLETED")
print(f"  Suppressed Contacts Checked : {len(suppressed_ids)}")
print(f"  Logs Deleted                : {total_purged}")
print("=" * 60)

import os
from database import get_db
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def verify_marketing_kpis():
    db = get_db()
    print("--- MARKETING KPI DIAGNOSTIC ---\n")

    # 1. Check Investment (Campaign Spend)
    campaigns = db.table("email_campaigns").select("*").execute()
    total_spend = sum([c.get("actual_spend") or 0 for c in campaigns.data])
    print(f"[INVESTMENT] Total calculated spend across all campaigns: ₦{total_spend:,.2f}")
    
    for c in campaigns.data:
        if (c.get("actual_spend") or 0) > 0:
            print(f"  - Campaign '{c['name']}': ₦{c['actual_spend']:,.2f}")

    # 2. Check Attributed Revenue
    # We look for paid invoices linked to a campaign
    revenue_res = db.table("invoices").select("amount, marketing_campaign_id").eq("status", "paid").not_.is_("marketing_campaign_id", "null").execute()
    total_revenue = sum([i["amount"] for i in revenue_res.data]) if revenue_res.data else 0
    conversions = len(revenue_res.data) if revenue_res.data else 0
    
    print(f"\n[REVENUE] Total attributed revenue (Paid Invoices): ₦{total_revenue:,.2f}")
    print(f"[CONVERSIONS] Total deals attributed to marketing: {conversions}")

    # 3. ROI & CAC Verification
    roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0
    cac = (total_spend / conversions) if conversions > 0 else 0
    
    print(f"\n[CALCULATED CARDS]")
    print(f"  → Expected Dashboard ROI: {roi:.2f}%")
    print(f"  → Expected Dashboard CAC: ₦{cac:,.2f}")

    # 4. Attribution Linkage Audit
    # Are there marketing contacts with LTV that we linked to campaigns?
    rev_contacts = db.table("marketing_contacts").select("first_name, last_name, total_revenue_attributed").gt("total_revenue_attributed", 0).execute()
    print(f"\n[LTV ENGINE] Found {len(rev_contacts.data)} contacts with attributed LTV revenue.")
    for contact in rev_contacts.data[:5]:
        print(f"  - {contact['first_name']} {contact['last_name']}: ₦{contact['total_revenue_attributed']:,.2f}")

if __name__ == "__main__":
    verify_marketing_kpis()

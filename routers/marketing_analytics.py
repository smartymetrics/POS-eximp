from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from database import get_db
from routers.auth import verify_token
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/overview")
async def get_marketing_overview(current_admin=Depends(verify_token)):
    """Fetch high-level KPIs for the marketing dashboard."""
    db = get_db()
    
    # 1. Total Contacts stats
    total_contacts = db.table("marketing_contacts").select("id", count="exact").execute().count
    subscribed = db.table("marketing_contacts").select("id", count="exact").eq("is_subscribed", True).execute().count
    
    # 2. Campaign Stats (Last 30 days)
    last_30_days = (datetime.utcnow() - timedelta(days=30)).isoformat()
    campaigns_res = db.table("email_campaigns").select("*").gte("created_at", last_30_days).execute()
    campaigns = campaigns_res.data or []
    
    sent_campaigns = [c for c in campaigns if c["status"] == "sent"]
    sent_count = len(sent_campaigns)

    # 3. Aggregated Open/Click Rate
    all_recs_res = db.table("campaign_recipients").select("open_count, click_count").execute()
    all_recs = all_recs_res.data or []
    
    total_delivered = len(all_recs)
    total_opened = len([r for r in all_recs if (r.get("open_count") or 0) > 0])
    total_clicked = len([r for r in all_recs if (r.get("click_count") or 0) > 0])
    
    avg_open_val = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
    avg_open = f"{avg_open_val:.1f}%"
    avg_click = f"{(total_clicked / total_delivered * 100):.1f}%" if total_delivered > 0 else "0%"
    
    # 4. Deltas (Month over Month)
    # Contact Growth this month
    new_this_month = db.table("marketing_contacts").select("id", count="exact").gte("created_at", last_30_days).execute().count or 0
    contact_delta = f"↑ {((new_this_month / (total_contacts - new_this_month) * 100) if (total_contacts - new_this_month) > 0 else 0):.1f}%"
    
    # 5. Growth Data (Last 14 days)
    growth_data = []
    for i in range(13, -1, -1):
        d = (datetime.utcnow() - timedelta(days=i)).date()
        date_str = d.isoformat()
        count = db.table("marketing_contacts").select("id", count="exact").lte("created_at", (d + timedelta(days=1)).isoformat()).execute().count or 0
        growth_data.append({"date": date_str, "count": count})

    return {
        "contacts": {
            "total": total_contacts or 0,
            "subscribed": subscribed or 0,
            "delta": contact_delta,
            "recent": new_this_month
        },
        "campaigns": {
            "sent_this_month": sent_count,
            "avg_open_rate": avg_open,
            "open_delta": "↑ 0.0% vs avg" # For future deep historical comparison
        },
        "engagement": {
            "total_opens": db.table("marketing_contacts").select("id", count="exact").gt("total_emails_opened", 0).execute().count or 0,
            "hot_leads": db.table("marketing_contacts").select("id", count="exact").gte("engagement_score", 50).execute().count or 0,
            "warm_leads": db.table("marketing_contacts").select("id", count="exact").lt("engagement_score", 50).gte("engagement_score", 30).execute().count or 0,
            "cold_leads": db.table("marketing_contacts").select("id", count="exact").lt("engagement_score", 30).execute().count or 0
        },
        "growth": growth_data
    }

@router.get("/campaign/{id}/report")
async def get_campaign_report(id: str, current_admin=Depends(verify_token)):
    """Fetch detailed stats for a single campaign."""
    db = get_db()
    
    # 1. Campaign metadata
    camp_res = db.table("email_campaigns").select("*").eq("id", id).execute()
    if not camp_res.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = camp_res.data[0]
    
    # 2. Recipient stats
    recs = db.table("campaign_recipients").select("status, open_count, click_count").eq("campaign_id", id).execute().data
    
    total = len(recs)
    delivered = len([r for r in recs if r["status"] == "delivered"])
    opened = len([r for r in recs if (r["open_count"] or 0) > 0])
    clicked = len([r for r in recs if (r["click_count"] or 0) > 0])
    bounced = len([r for r in recs if r["status"] == "bounced"])
    
    return {
        "campaign_id": id,
        "name": campaign["name"],
        "subject": campaign["subject_a"],
        "stats": {
            "total_recipients": total,
            "delivered": {"count": delivered, "percent": (delivered/total*100) if total > 0 else 0},
            "opened": {"count": opened, "percent": (opened/total*100) if total > 0 else 0},
            "clicked": {"count": clicked, "percent": (clicked/total*100) if total > 0 else 0},
            "bounced": {"count": bounced, "percent": (bounced/total*100) if total > 0 else 0}
        }
    }

@router.get("/campaign/{id}/recipients")
async def get_campaign_recipients(id: str, current_admin=Depends(verify_token)):
    """Fetch the list of individual recipients for a campaign with their engagement."""
    db = get_db()
    
    # Fetch recipients joined with contact details
    res = db.table("campaign_recipients")\
        .select("*, marketing_contacts(first_name, last_name, email)")\
        .eq("campaign_id", id)\
        .order("open_count", desc=True)\
        .execute()
        
    return res.data or []

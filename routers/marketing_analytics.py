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
    # Calculate across all sent campaigns in history
    all_recs_res = db.table("campaign_recipients").select("open_count, click_count").execute()
    all_recs = all_recs_res.data or []
    
    total_delivered = len(all_recs)
    total_opened = len([r for r in all_recs if (r.get("open_count") or 0) > 0])
    total_clicked = len([r for r in all_recs if (r.get("click_count") or 0) > 0])
    
    avg_open = f"{(total_opened / total_delivered * 100):.1f}%" if total_delivered > 0 else "0%"
    avg_click = f"{(total_clicked / total_delivered * 100):.1f}%" if total_delivered > 0 else "0%"
    
    return {
        "contacts": {
            "total": total_contacts or 0,
            "subscribed": subscribed or 0,
            "unsubscribed": (total_contacts or 0) - (subscribed or 0)
        },
        "campaigns": {
            "sent_this_month": sent_count,
            "avg_open_rate": avg_open,
            "avg_click_rate": avg_click
        },
        "engagement": {
            "hot_leads": db.table("marketing_contacts").select("id", count="exact").gte("engagement_score", 70).execute().count or 0,
            "warm_leads": db.table("marketing_contacts").select("id", count="exact").lt("engagement_score", 70).gte("engagement_score", 30).execute().count or 0
        }
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

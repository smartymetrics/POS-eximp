from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from database import get_db, db_execute
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
    
    # 2. Campaign Stats — fetch ALL campaigns (not limited to 30 days) so historical spend is included
    campaigns_res = await db_execute(lambda: db.table("email_campaigns").select("*").execute())
    campaigns = campaigns_res.data or []
    
    # Count "sent" this month for KPI display
    last_30_days = (datetime.utcnow() - timedelta(days=30)).isoformat()
    sent_campaigns = [c for c in campaigns if c["status"] == "sent"]
    sent_count = len([c for c in sent_campaigns if c.get("created_at", "") >= last_30_days])

    # 3. Aggregated Open/Click Rate (all time)
    all_recs_res = await db_execute(lambda: db.table("campaign_recipients").select("open_count, click_count").execute())
    all_recs = all_recs_res.data or []
    
    total_delivered = len(all_recs)
    total_opened = len([r for r in all_recs if (r.get("open_count") or 0) > 0])
    total_clicked = len([r for r in all_recs if (r.get("click_count") or 0) > 0])
    
    avg_open_val = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
    avg_open = f"{avg_open_val:.1f}%"
    open_delta = f"↑ {avg_open_val:.1f}% vs avg" if avg_open_val > 0 else "↑ 0% vs avg"
    
    # 4. Deltas (Month over Month)
    new_this_month = db.table("marketing_contacts").select("id", count="exact").gte("created_at", last_30_days).execute().count or 0
    previous_total = total_contacts - new_this_month
    
    if previous_total == 0 and new_this_month > 0:
        delta_val = 100.0
    elif previous_total > 0:
        delta_val = (new_this_month / previous_total) * 100
    else:
        delta_val = 0.0
        
    direction = "↑" if delta_val > 0 else "→" if delta_val == 0 else "↓"
    contact_delta = f"{direction} {delta_val:.1f}%"
    
    # 5. Growth Data (Last 14 days)
    growth_data = []
    for i in range(13, -1, -1):
        d = (datetime.utcnow() - timedelta(days=i)).date()
        date_str = d.isoformat()
        count = db.table("marketing_contacts").select("id", count="exact").lte("created_at", (d + timedelta(days=1)).isoformat()).execute().count or 0
        growth_data.append({"date": date_str, "count": count})

    # 6. Total Attributed Revenue & Segment ROI/CPA
    try:
        revenue_res = await db_execute(lambda: db.table("invoices").select("amount, marketing_campaign_id").not_.is_("marketing_campaign_id", "null").eq("status", "paid").execute())
        total_revenue = sum([i["amount"] for i in revenue_res.data]) if revenue_res.data else 0
        attributed_invoices = revenue_res.data or []
    except Exception:
        total_revenue = 0
        attributed_invoices = []

    # Total spend: use actual_spend if set, otherwise fall back to budget
    total_spend = sum([(c.get("actual_spend") or c.get("budget") or 0) for c in campaigns])
    
    # Set ROI to 0 if there's no revenue yet to avoid an alarming -100% for new campaigns
    if total_revenue == 0:
        overall_roi = 0
    else:
        overall_roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0

    cpa = (total_spend / len(attributed_invoices)) if attributed_invoices and total_spend > 0 else 0

    # Calculate Segment Details
    segment_data = {}
    if campaigns:
        camp_map = {c["id"]: {
            "seg": c.get("target_segment") or "Uncategorized", 
            "spend": (c.get("actual_spend") or c.get("budget") or 0)
        } for c in campaigns}
        
        for inv in attributed_invoices:
            attr = camp_map.get(inv.get("marketing_campaign_id"), {"seg": "Unknown", "spend": 0})
            seg = attr["seg"]
            if seg not in segment_data:
                segment_data[seg] = {"revenue": 0, "spend": 0, "conversions": 0}
            segment_data[seg]["revenue"] += inv["amount"]
            segment_data[seg]["conversions"] += 1
            
        for c in campaigns:
            seg = c.get("target_segment") or "Uncategorized"
            if seg not in segment_data:
                segment_data[seg] = {"revenue": 0, "spend": 0, "conversions": 0}
            segment_data[seg]["spend"] += (c.get("actual_spend") or c.get("budget") or 0)
    
    segment_stats = []
    for k, v in segment_data.items():
        segment_stats.append({
            "segment": k,
            "revenue": v["revenue"],
            "spend": v["spend"],
            "roi": 0 if v["revenue"] == 0 else ((v["revenue"] - v["spend"]) / v["spend"] * 100) if v["spend"] > 0 else 0,
            "cpa": (v["spend"] / v["conversions"]) if v["conversions"] > 0 else 0
        })
    segment_stats.sort(key=lambda x: x["revenue"], reverse=True)

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
            "open_delta": open_delta,
            "total_revenue": total_revenue,
            "total_spend": total_spend,
            "overall_roi": overall_roi,
            "avg_cpa": cpa
        },
        "engagement": {
            "total_opens": db.table("marketing_contacts").select("id", count="exact").gt("total_emails_opened", 0).execute().count or 0,
            "hot_leads": db.table("marketing_contacts").select("id", count="exact").gte("engagement_score", 50).execute().count or 0,
            "warm_leads": db.table("marketing_contacts").select("id", count="exact").lt("engagement_score", 50).gte("engagement_score", 30).execute().count or 0,
            "cold_leads": db.table("marketing_contacts").select("id", count="exact").lt("engagement_score", 30).execute().count or 0
        },
        "segment_stats": segment_stats,
        "growth": growth_data
    }

@router.get("/campaign/{id}/report")
async def get_campaign_report(id: str, current_admin=Depends(verify_token)):
    """Fetch detailed stats for a single campaign."""
    db = get_db()
    
    # 1. Campaign metadata
    camp_res = await db_execute(lambda: db.table("email_campaigns").select("*").eq("id", id).execute())
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

@router.get("/campaign/{id}/conversions")
async def get_campaign_conversions(id: str, current_admin=Depends(verify_token)):
    """Fetch the list of actual invoices and clients that make up the campaign ROI."""
    db = get_db()
    
    # Fetch paid invoices attributed to this campaign joined with client names
    res = db.table("invoices")\
        .select("invoice_number, amount, paid_at, clients(full_name)")\
        .eq("marketing_campaign_id", id)\
        .eq("status", "paid")\
        .order("paid_at", desc=True)\
        .execute()
        
    return res.data or []

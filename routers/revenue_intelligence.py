from fastapi import APIRouter, Depends, HTTPException
from database import get_db, db_execute
from routers.auth import verify_token
from typing import List, Dict, Any
from decimal import Decimal

router = APIRouter()

@router.get("/attribution/summary")
async def get_attribution_summary(current_admin=Depends(verify_token)):
    """
    Returns total revenue attributed to each marketing campaign.
    HubSpot-style 'Closed-Loop' Reporting.
    """
    db = get_db()
    
    # 1. Fetch campaigns
    campaigns_res = await db_execute(lambda: db.table("email_campaigns").select("id, name").execute())
    campaigns = campaigns_res.data or []
    
    # 2. Fetch attributed invoices (only non-voided)
    invoices_res = db.table("invoices")\
        .select("amount, amount_paid, marketing_campaign_id")\
        .neq("status", "voided")\
        .not_.is_("marketing_campaign_id", "null")\
        .execute()
    invoices = invoices_res.data or []
    
    # 3. Aggregate
    summary = []
    campaign_map = {c["id"]: c["name"] for c in campaigns}
    
    attribution_data = {}
    for inv in invoices:
        camp_id = inv["marketing_campaign_id"]
        if camp_id not in attribution_data:
            attribution_data[camp_id] = {"revenue": 0, "collected": 0, "deal_count": 0}
        
        attribution_data[camp_id]["revenue"] += float(inv["amount"])
        attribution_data[camp_id]["collected"] += float(inv["amount_paid"])
        attribution_data[camp_id]["deal_count"] += 1
        
    for camp_id, stats in attribution_data.items():
        summary.append({
            "campaign_id": camp_id,
            "campaign_name": campaign_map.get(camp_id, "Unknown Campaign"),
            "total_revenue": stats["revenue"],
            "total_collected": stats["collected"],
            "deal_count": stats["deal_count"]
        })
        
    # Sort by revenue
    summary.sort(key=lambda x: x["total_revenue"], reverse=True)
    return summary

@router.get("/forecast/weighted")
async def get_weighted_forecast(current_admin=Depends(verify_token)):
    """
    Professional Weighted Pipeline Forecasting.
    Unpaid = 10% probability
    Partial = 60% probability
    Paid = 100% probability
    """
    db = get_db()
    
    # Fetch all active (non-voided) invoices
    invoices_res = await db_execute(lambda: db.table("invoices").select("amount, amount_paid, status").neq("status", "voided").execute())
    invoices = invoices_res.data or []
    
    total_pipeline = 0
    weighted_value = 0
    collected = 0
    
    for inv in invoices:
        amount = float(inv["amount"])
        paid = float(inv["amount_paid"])
        status = inv.get("status", "unpaid")
        
        total_pipeline += amount
        collected += paid
        
        # Weighted logic
        if status == "paid":
            weighted_value += amount
        elif status == "partial":
            # Already collected money is 100%, remaining is 60%
            remaining = amount - paid
            weighted_value += paid + (remaining * 0.6)
        else: # unpaid
            weighted_value += (amount * 0.1)
            
    return {
        "total_pipeline_value": total_pipeline,
        "weighted_forecast_value": weighted_value,
        "actual_collected": collected,
        "pipeline_gap": total_pipeline - collected
    }

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from typing import List, Optional
from database import supabase
from models import SalesRepCreate, SalesRepUpdate, ResolveUnmatchedRequest
from routers.auth import get_current_admin
from routers.analytics import log_activity

router = APIRouter()

@router.get("")
async def get_sales_reps(admin: dict = Depends(get_current_admin)):
    """List all sales representatives with basic stats."""
    res = supabase.table("sales_reps").select("*").order("name").execute()
    reps = res.data
    
    # Get deal counts from invoices (excluding voided)
    inv_res = supabase.table("invoices").select("sales_rep_name").neq("status", "voided").execute()
    counts = {}
    for inv in inv_res.data:
        name = inv.get("sales_rep_name")
        if name:
            counts[name] = counts.get(name, 0) + 1
            
    for rep in reps:
        rep["total_deals"] = counts.get(rep["name"], 0)
        
    return reps

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_sales_rep(
    rep: SalesRepCreate, 
    background_tasks: BackgroundTasks,
    admin: dict = Depends(get_current_admin)
):
    # Use jsonable_encoder to handle Decimal/date types for Supabase
    rep_data = jsonable_encoder(rep)
    res = supabase.table("sales_reps").insert(rep_data).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create rep")
    
    new_rep = res.data[0]
    background_tasks.add_task(
        log_activity,
        "sales_rep_created",
        f"Added new sales rep: {new_rep['name']}",
        performed_by=admin["sub"]
    )
    return {"message": "Sales representative added", "rep": new_rep}

@router.patch("/{rep_id}")
async def update_sales_rep(
    rep_id: str, 
    rep_update: SalesRepUpdate, 
    background_tasks: BackgroundTasks,
    admin: dict = Depends(get_current_admin)
):
    """Update sales representative details."""
    if admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage reps")
        
    # Filter out None values and encode for Supabase
    update_data = jsonable_encoder(rep_update, exclude_none=True)
    res = supabase.table("sales_reps").update(update_data).eq("id", rep_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Rep not found")
        
    background_tasks.add_task(
        log_activity,
        "sales_rep_updated",
        f"Updated sales rep: {res.data[0]['name']}",
        performed_by=admin["sub"]
    )
    return res.data[0]

@router.get("/unmatched")
async def get_unmatched_reps(admin: dict = Depends(get_current_admin)):
    """List names from forms that don't match any registered rep."""
    res = supabase.table("unmatched_reps").select("*").eq("is_resolved", False).order("times_seen", desc=True).execute()
    return res.data

@router.post("/resolve")
async def resolve_unmatched_rep(
    req: ResolveUnmatchedRequest, 
    background_tasks: BackgroundTasks,
    admin: dict = Depends(get_current_admin)
):
    """Map an unmatched name to a registered rep and update historical invoices."""
    if admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can resolve names")
        
    # 1. Get the unmatched record
    unmatched = supabase.table("unmatched_reps").select("*").eq("id", req.unmatched_id).execute()
    if not unmatched.data:
        raise HTTPException(status_code=404, detail="Unmatched record not found")
    
    unmatched_name = unmatched.data[0]["name_from_form"]
    
    # 2. Get the target rep
    target_rep = supabase.table("sales_reps").select("*").eq("id", req.target_rep_id).execute()
    if not target_rep.data:
        raise HTTPException(status_code=404, detail="Target rep not found")
        
    target_name = target_rep.data[0]["name"]
    
    # 3. Update all invoices that used the unmatched name
    supabase.table("invoices").update({"sales_rep_name": target_name}).eq("sales_rep_name", unmatched_name).execute()
    
    # 4. Mark as resolved
    supabase.table("unmatched_reps").update({
        "is_resolved": True, 
        "resolved_to": req.target_rep_id
    }).eq("id", req.unmatched_id).execute()
    
    background_tasks.add_task(
        log_activity,
        "rep_name_resolved",
        f"Resolved unmatched name '{unmatched_name}' to rep '{target_name}'",
        performed_by=admin["sub"]
    )
    
    return {"message": f"Successfully mapped '{unmatched_name}' to '{target_name}'"}

@router.get("/{rep_id}/stats")
async def get_rep_stats(rep_id: str, admin: dict = Depends(get_current_admin)):
    """Get detailed performance stats for a specific rep."""
    rep = supabase.table("sales_reps").select("*").eq("id", rep_id).execute()
    if not rep.data:
        raise HTTPException(status_code=404, detail="Rep not found")
    
    rep_name = rep.data[0]["name"]
    
    # Simple aggregates
    inv_res = supabase.table("invoices").select("amount, amount_paid, status").eq("sales_rep_name", rep_name).neq("status", "voided").execute()
    
    stats = {
        "total_deals": len(inv_res.data),
        "total_revenue": sum(float(i["amount"]) for i in inv_res.data),
        "total_collected": sum(float(i["amount_paid"]) for i in inv_res.data),
        "fully_paid_deals": len([i for i in inv_res.data if i["status"] == "paid"]),
    }
    
    if stats["total_revenue"] > 0:
        stats["collection_rate"] = (stats["total_collected"] / stats["total_revenue"]) * 100
    else:
        stats["collection_rate"] = 0
        
    return {"rep": rep.data[0], "stats": stats}

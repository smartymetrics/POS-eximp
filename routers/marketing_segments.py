from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import get_db, db_execute
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime, timedelta
from marketing_service import apply_segment_filters, get_financial_segment_contacts

router = APIRouter()

class SegmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    segment_type: str = "static" # static / dynamic
    filter_rules: Optional[List[Dict[str, Any]]] = None

@router.get("/")
async def list_segments(current_admin=Depends(verify_token)):
    db = get_db()
    result = await db_execute(lambda: db.table("marketing_segments").select("*").execute())
    return result.data

@router.get("/contact/{contact_id}")
async def get_contact_segments(contact_id: str, current_admin=Depends(verify_token)):
    """Fetch all static segments a specific contact belongs to."""
    db = get_db()
    res = db.table("marketing_segment_contacts")\
        .select("marketing_segments(*)")\
        .eq("contact_id", contact_id)\
        .execute()
    static_segments = [r["marketing_segments"] for r in res.data if r.get("marketing_segments")]
    return static_segments

@router.post("/")
async def create_segment(data: SegmentCreate, current_admin=Depends(verify_token)):
    db = get_db()
    segment_data = {
        **data.dict(),
        "created_by": current_admin["sub"]
    }
    result = await db_execute(lambda: db.table("marketing_segments").insert(segment_data).execute())
    
    await log_activity(
        "marketing_segment_created",
        f"New marketing segment '{data.name}' created.",
        current_admin["sub"]
    )
    return result.data[0]

@router.delete("/{id}")
async def delete_segment(id: str, current_admin=Depends(verify_token)):
    db = get_db()
    await db_execute(lambda: db.table("marketing_segments").delete().eq("id", id).execute())
    return {"status": "ok"}

@router.get("/{id}/contacts")
async def get_segment_contacts(id: str, current_admin=Depends(verify_token)):
    """Preview contacts who match a dynamic or static segment."""
    db = get_db()
    
    # Handle Smart Segments
    if id == 'engaged':
        res = await db_execute(lambda: db.table("marketing_contacts").select("*").gt("total_emails_opened", 0).eq("is_subscribed", True).execute())
        return res.data
    elif id == 'hot':
        res = await db_execute(lambda: db.table("marketing_contacts").select("*").gt("engagement_score", 50).eq("is_subscribed", True).execute())
        return res.data
    elif id == 'recent':
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        res = await db_execute(lambda: db.table("marketing_contacts").select("*").gt("created_at", thirty_days_ago).eq("is_subscribed", True).execute())
        return res.data
    elif id.startswith("financial_"):
        return get_financial_segment_contacts(id)

    # Handle Custom Segments
    seg_res = await db_execute(lambda: db.table("marketing_segments").select("*").eq("id", id).execute())
    if not seg_res.data:
        raise HTTPException(status_code=404, detail="Segment not found")
    segment = seg_res.data[0]
    
    if segment["segment_type"] == "static":
        res = db.table("marketing_segment_contacts")\
            .select("marketing_contacts(*)")\
            .eq("segment_id", id)\
            .execute()
        return [r["marketing_contacts"] for r in res.data if r.get("marketing_contacts")]
    
    rules = segment.get("filter_rules") or []
    query = db.table("marketing_contacts").select("*").eq("is_subscribed", True)
    query = apply_segment_filters(query, rules)
    result = await db_execute(lambda: query.limit(100).execute())
    return result.data

@router.post("/preview")
async def preview_segment_rules(rules: List[Dict[str, Any]], current_admin=Depends(verify_token)):
    """Count contacts who match provided rules (without saving segment)."""
    db = get_db()
    query = db.table("marketing_contacts").select("id", count="exact").eq("is_subscribed", True)
    query = apply_segment_filters(query, rules)
    result = await db_execute(lambda: query.execute())
    return {"count": result.count or 0}

@router.get("/{id}/count")
async def get_segment_count(id: str, current_admin=Depends(verify_token)):
    """Get total count for an existing segment."""
    db = get_db()
    
    if id == 'engaged':
        res = await db_execute(lambda: db.table("marketing_contacts").select("id", count="exact").gt("total_emails_opened", 0).eq("is_subscribed", True).execute())
        return {"count": res.count or 0}
    elif id == 'hot':
        res = await db_execute(lambda: db.table("marketing_contacts").select("id", count="exact").gt("engagement_score", 50).eq("is_subscribed", True).execute())
        return {"count": res.count or 0}
    elif id == 'recent':
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        res = await db_execute(lambda: db.table("marketing_contacts").select("id", count="exact").gt("created_at", thirty_days_ago).eq("is_subscribed", True).execute())
        return {"count": res.count or 0}
    elif id.startswith("financial_"):
        contacts = get_financial_segment_contacts(id)
        return {"count": len(contacts)}
        
    seg_res = await db_execute(lambda: db.table("marketing_segments").select("*").eq("id", id).execute())
    if not seg_res.data:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    segment = seg_res.data[0]
    if segment["segment_type"] == "static":
        res = await db_execute(lambda: db.table("marketing_segment_contacts").select("contact_id", count="exact").eq("segment_id", id).execute())
        return {"count": res.count or 0}

    rules = segment.get("filter_rules") or []
    query = db.table("marketing_contacts").select("id", count="exact").eq("is_subscribed", True)
    query = apply_segment_filters(query, rules)
    result = await db_execute(lambda: query.execute())
    return {"count": result.count or 0}

@router.post("/{id}/members")
async def add_segment_member(id: str, contact_id: str, current_admin=Depends(verify_token)):
    """Manually add a contact to a static segment."""
    db = get_db()
    # 1. Verify it's a static segment
    seg = await db_execute(lambda: db.table("marketing_segments").select("segment_type").eq("id", id).execute())
    if not seg.data or seg.data[0]["segment_type"] != "static":
        raise HTTPException(status_code=400, detail="Members can only be manually added to static segments.")
    
    # 2. Insert
    db.table("marketing_segment_contacts").upsert({
        "segment_id": id,
        "contact_id": contact_id
    }).execute()
    
    return {"status": "ok"}

@router.delete("/{id}/members/{contact_id}")
async def remove_segment_member(id: str, contact_id: str, current_admin=Depends(verify_token)):
    """Remove a contact from a static segment."""
    db = get_db()
    await db_execute(lambda: db.table("marketing_segment_contacts").delete().eq("segment_id", id).eq("contact_id", contact_id).execute())
    return {"status": "ok"}



@router.get("/diagnostic/financial-segmentation")
async def test_financial_segmentation(current_admin=Depends(verify_token)):
    """TEST ENDPOINT to verify we can group clients by payment status across invoices."""
    db = get_db()
    
    invoices_res = db.table("invoices")\
        .select("amount, amount_paid, due_date, status, client_id, clients(email, full_name)")\
        .neq("status", "voided")\
        .execute()
        
    invoices = invoices_res.data or []
    
    client_financials = {}
    today = datetime.utcnow().date().isoformat()
    
    for inv in invoices:
        client = inv.get("clients")
        if not client: continue
        email = client.get("email")
        if not email: continue
        
        email = email.lower().strip()
        
        if email not in client_financials:
            client_financials[email] = {
                "name": client.get("full_name"),
                "total_invoiced": 0,
                "total_paid": 0,
                "has_overdue": False,
                "outstanding": 0
            }
        
        amount = float(inv.get("amount") or 0)
        paid = float(inv.get("amount_paid") or 0)
        due_date = inv.get("due_date", "")
        
        client_financials[email]["total_invoiced"] += amount
        client_financials[email]["total_paid"] += paid
        
        if paid < amount and due_date and due_date < today:
            client_financials[email]["has_overdue"] = True
            
    results = {"overdue": [], "outstanding": [], "paid_fully": []}
    
    for email, stats in client_financials.items():
        stats["outstanding"] = stats["total_invoiced"] - stats["total_paid"]
        
        if stats["has_overdue"]:
            results["overdue"].append(email)
        elif stats["outstanding"] > 0:
            results["outstanding"].append(email)
        elif stats["total_invoiced"] > 0:
            results["paid_fully"].append(email)
            
    all_contacts_res = await db_execute(lambda: db.table("marketing_contacts").select("email").execute())
    marketing_emails = {c["email"].lower() for c in all_contacts_res.data}
    
    financial_emails = set(client_financials.keys())
    missing_from_marketing = list(financial_emails - marketing_emails)
    
    return {
        "summary": {
            "total_invoices": len(invoices),
            "overdue_clients": len(results["overdue"]),
            "outstanding_clients": len(results["outstanding"]),
            "paid_fully_clients": len(results["paid_fully"])
        },
        "integration": {
            "total_marketing_contacts": len(marketing_emails),
            "financial_clients_missing_from_marketing": len(missing_from_marketing),
            "sample_missing": missing_from_marketing[:5]
        }
    }

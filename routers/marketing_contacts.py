from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime
import csv
import io

router = APIRouter()

class ContactCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    tags: Optional[List[str]] = None
    contact_type: str = "lead" # lead / client
    source: str = "manual"

class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[List[str]] = None
    is_subscribed: Optional[bool] = None
    engagement_score: Optional[int] = None
    contact_type: Optional[str] = None

@router.get("/")
async def list_contacts(current_admin=Depends(verify_token), type: Optional[str] = None, q: Optional[str] = None):
    db = get_db()
    query = db.table("marketing_contacts").select("*")
    
    if type:
        query = query.eq("contact_type", type)
    if q:
        query = query.ilike("email", f"%{q}%")
        
    result = query.order("created_at", desc=True).execute()
    return result.data

@router.post("/")
async def create_contact(data: ContactCreate, current_admin=Depends(verify_token)):
    db = get_db()
    
    # Check if contact exists
    check = db.table("marketing_contacts").select("id").eq("email", data.email).execute()
    if check.data:
        raise HTTPException(status_code=400, detail="Contact with this email already exists.")
    
    result = db.table("marketing_contacts").insert(data.dict()).execute()
    
    await log_activity(
        "marketing_contact_created",
        f"Contact {data.email} added manually to marketing list.",
        current_admin["sub"]
    )
    return result.data[0]

@router.put("/{id}")
async def update_contact(id: str, data: ContactUpdate, current_admin=Depends(verify_token)):
    db = get_db()
    update_dict = {k: v for k, v in data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow().isoformat()
    
    result = db.table("marketing_contacts").update(update_dict).eq("id", id).execute()
    return result.data[0]

@router.get("/{id}")
async def get_contact(id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = db.table("marketing_contacts").select("*").eq("id", id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Contact not found")
    return res.data[0]

@router.post("/import")
async def import_contacts(source: Optional[str] = "csv_import", file: UploadFile = File(...), current_admin=Depends(verify_token)):
    """Bulk import contacts from CSV with an optional source label."""
    db = get_db()
    content = await file.read()
    string_io = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(string_io)
    
    contacts_to_insert = []
    skipped_count = 0
    duplicate_count = 0
    
    for row in reader:
        email = row.get("email") or row.get("Email")
        if not email or "@" not in email:
            skipped_count += 1
            continue
            
        first_name = row.get("first_name") or row.get("First Name") or ""
        last_name = row.get("last_name") or row.get("Last Name") or ""
        phone = row.get("phone") or row.get("Phone") or ""
        tags = [t.strip() for t in (row.get("tags") or "").split(",") if t.strip()]
        
        # Simple duplicate check inside the loop (better to do bulk upsert in Postgres)
        contacts_to_insert.append({
            "email": email.lower().strip(),
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "tags": tags,
            "source": source or "csv_import",
            "contact_type": "lead"
        })

    if contacts_to_insert:
        # We use upsert on email to handle duplicates
        result = db.table("marketing_contacts").upsert(contacts_to_insert, on_conflict="email").execute()
        import_count = len(result.data)
    else:
        import_count = 0

    return {
        "message": f"Import complete. {import_count} contacts processed.",
        "skipped_invalid": skipped_count,
        "import_count": import_count
    }

@router.post("/sync-clients")
async def sync_clients(current_admin=Depends(verify_token)):
    """Legacy: One-time sync of all current clients into marketing_contacts."""
    db = get_db()
    clients = db.table("clients").select("id, full_name, email, phone").execute().data
    
    marketing_entries = []
    for c in clients:
        names = (c["full_name"] or "Valued Client").split(" ", 1)
        first = names[0]
        last = names[1] if len(names) > 1 else ""
        
        marketing_entries.append({
            "client_id": c["id"],
            "first_name": first,
            "last_name": last,
            "email": c["email"].lower().strip(),
            "phone": c["phone"],
            "source": "ecoms_client",
            "contact_type": "client"
        })
    
    if marketing_entries:
        res = db.table("marketing_contacts").upsert(marketing_entries, on_conflict="email").execute()
        return {"synced_count": len(res.data)}
    return {"synced_count": 0}
@router.get("/{id}/history")
async def get_contact_history(id: str, current_admin=Depends(verify_token)):
    """Fetch the full interaction history for a contact."""
    db = get_db()
    
    # 1. Fetch contact details
    contact_res = db.table("marketing_contacts").select("*").eq("id", id).execute()
    if not contact_res.data:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # 2. Fetch campaign interactions
    interactions = db.table("campaign_recipients")\
        .select("status, opened_at, clicked_at, email_campaigns(name)")\
        .eq("contact_id", id)\
        .execute()
        
    # 3. Build a flat timeline
    timeline = []
    for inter in interactions.data:
        camp_name = inter["email_campaigns"]["name"] if inter.get("email_campaigns") else "Unknown Campaign"
        if inter.get("opened_at"):
            timeline.append({"type": "open", "campaign_name": camp_name, "timestamp": inter["opened_at"]})
        if inter.get("clicked_at"):
            timeline.append({"type": "click", "campaign_name": camp_name, "timestamp": inter["clicked_at"]})
            
    # Sort by recent
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)
    return timeline

@router.post("/sync-all-stats")
async def sync_all_marketing_stats(current_admin=Depends(verify_token)):
    """Bulk recalculates marketing stats for ALL campaigns and contacts."""
    db = get_db()
    
    # 1. Fetch all recipients with activity
    rec_res = db.table("campaign_recipients").select("campaign_id, contact_id, opened_at, clicked_at").execute()
    recs = rec_res.data or []
    
    # 2. Aggregate Campaigns
    camp_stats = {}
    cont_stats = {}
    
    for r in recs:
        cid = r["campaign_id"]
        uid = r["contact_id"]
        
        if cid not in camp_stats: camp_stats[cid] = {"opens": 0, "clicks": 0}
        if uid not in cont_stats: cont_stats[uid] = {"opens": 0, "clicks": 0}
        
        if r.get("opened_at"):
            camp_stats[cid]["opens"] += 1
            cont_stats[uid]["opens"] += 1
        if r.get("clicked_at"):
            camp_stats[cid]["clicks"] += 1
            cont_stats[uid]["clicks"] += 1
            
    # 3. Update All Campaigns
    for cid, stats in camp_stats.items():
        db.table("email_campaigns").update({
            "total_opens": stats["opens"],
            "total_clicks": stats["clicks"]
        }).eq("id", cid).execute()
        
    # 4. Update All Contacts
    updated_count = 0
    for uid, stats in cont_stats.items():
        # Score calculation: 5 per open, 10 per click, max 100
        score = min(100, (stats["opens"] * 5) + (stats["clicks"] * 10))
        db.table("marketing_contacts").update({
            "total_emails_opened": stats["opens"],
            "total_emails_clicked": stats["clicks"],
            "engagement_score": score
        }).eq("id", uid).execute()
        updated_count += 1
        
    return {
        "message": "Bulk stats sync complete.",
        "campaigns_updated": len(camp_stats),
        "contacts_updated": updated_count
    }

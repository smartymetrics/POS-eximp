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
    first_name: Optional[str]
    last_name: Optional[str]
    email: str
    phone: Optional[str]
    tags: Optional[List[str]]
    contact_type: str = "lead" # lead / client
    source: str = "manual"

class ContactUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    tags: Optional[List[str]]
    is_subscribed: Optional[bool]
    engagement_score: Optional[int]

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

@router.post("/import")
async def import_contacts(file: UploadFile = File(...), current_admin=Depends(verify_token)):
    """Bulk import contacts from CSV."""
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
            "source": "csv_import",
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

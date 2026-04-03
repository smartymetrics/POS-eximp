from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
from database import get_db
from routers.auth import verify_token
from routers.analytics import log_activity
from datetime import datetime
import os
import uuid
import uuid as uuid_pkg

router = APIRouter()

# TODO: Connect to Supabase Storage
# For now, we'll store media metadata in the table and assume the user provides a URL 
# or we use a temporary local storage if needed.

@router.get("/")
async def list_media(current_admin=Depends(verify_token), q: Optional[str] = None):
    db = get_db()
    result = db.table("media_library").select("*").order("created_at", desc=True).execute()
    return result.data

@router.post("/upload")
async def upload_media(file: UploadFile = File(...), current_admin=Depends(verify_token)):
    """Upload a file to the media library."""
    db = get_db()
    
    # Check mime type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only images are allowed in the marketing media library.")

    # 1. Generate unique filename
    ext = file.filename.split(".")[-1]
    unique_filename = f"{uuid_pkg.uuid4()}.{ext}"
    
    # 2. Upload to Supabase Storage (Mocked for now - returning a generic URL)
    # The actual implementation would use a client for Supabase Storage.
    file_url = f"https://placeholder.eximps-cloves.com/media/{unique_filename}"
    
    # 3. Save metadata
    media_data = {
        "filename": unique_filename,
        "original_filename": file.filename,
        "file_url": file_url,
        "mime_type": file.content_type,
        "uploaded_by": current_admin["sub"]
    }
    
    result = db.table("media_library").insert(media_data).execute()
    
    await log_activity(
        "marketing_media_uploaded",
        f"New media file uploaded: {file.filename}",
        current_admin["sub"]
    )
    
    return result.data[0]

@router.delete("/{id}")
async def delete_media(id: str, current_admin=Depends(verify_token)):
    db = get_db()
    db.table("media_library").delete().eq("id", id).execute()
    return {"status": "ok"}

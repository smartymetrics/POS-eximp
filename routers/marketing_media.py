from fastapi import APIRouter, Depends, Request, HTTPException, status
from database import get_db, SUPABASE_URL, db_execute
from routers.auth import verify_token
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/upload")
async def upload_media(request: Request, current_admin=Depends(verify_token)):
    """
    Handles file uploads from GrapesJS Asset Manager.
    Uses 'Request' directly to handle varying form field names ('files[]', 'files', 'file').
    Saves to Supabase Storage and records metadata.
    """
    try:
        form = await request.form()
        
        # Find the file in the form data regardless of the field name
        file = None
        for key, value in form.items():
            if hasattr(value, "filename") and value.filename:
                file = value
                break
                
        if not file:
            raise HTTPException(status_code=400, detail="No file payload found in the request form.")

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")

        db = get_db()
        
        # Generate unique filename with date-based folder structure (YYYY/MM)
        ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        now = datetime.now()
        date_folder = f"{now.year}/{now.month:02d}"
        unique_filename = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
        
        full_storage_path = f"{date_folder}/{unique_filename}"
        
        # 1. Upload to Supabase Storage bucket 'marketing'
        res = db.storage.from_("marketing").upload(
            path=full_storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
        
        # 2. Get Public URL
        file_url = f"{SUPABASE_URL}/storage/v1/object/public/marketing/{full_storage_path}"
        
        # 3. Save metadata to 'media_library' table
        # NOTE: Removed 'storage_path' to align with the actual database schema
        media_data = {
            "filename": unique_filename,
            "original_filename": file.filename,
            "file_url": file_url,
            "mime_type": file.content_type,
            "uploaded_by": current_admin["sub"]
        }
        
        await db_execute(lambda: db.table("media_library").insert(media_data).execute())

        # GrapesJS expects a specific JSON response format
        return {"data": [file_url]}

    except Exception as e:
        print(f"❌ SUPABASE UPLOAD CRASH: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_media(current_admin=Depends(verify_token)):
    db = get_db()
    try:
        result = await db_execute(lambda: db.table("media_library").select("*").order("created_at", desc=True).execute())
        return {"data": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
async def delete_media(id: str, current_admin=Depends(verify_token)):
    """TASK 5: Delete media from storage and library."""
    db = get_db()
    # 1. Fetch the media record
    res = await db_execute(lambda: db.table("media_library").select("*").eq("id", id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Media not found")
    
    media = res.data[0]
    file_url = media["file_url"]
    
    # Extract storage path from URL: {SUPABASE_URL}/storage/v1/object/public/marketing/{date_folder}/{filename}
    # Path is everything after /marketing/
    storage_path = file_url.split("/marketing/")[-1]
    
    # 2. Delete from Storage
    try:
        db.storage.from_("marketing").remove([storage_path])
    except Exception as e:
        # Log and continue even if storage delete fails
        print(f"Error deleting from storage: {e}")
        
    # 3. Delete from DB
    await db_execute(lambda: db.table("media_library").delete().eq("id", id).execute())
    
    return {"message": "Media deleted.", "id": id}

from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import get_db, SUPABASE_URL, db_execute
from subscription_service import SubscriptionService
import uuid
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/subscribe", response_class=HTMLResponse)
async def get_subscription_form(request: Request, rep: str = None):
    """
    Renders the custom property subscription form.
    Branding: Uses the 'rep' query param to identify the consultant.
    """
    db = get_db()
    rep_data = None
    
    if rep:
        rep_res = None
        try:
            # First, assume it's a unique ID (UUID)
            uuid_val = uuid.UUID(rep)
            rep_res = await db_execute(lambda: db.table("sales_reps").select("*").eq("id", str(uuid_val)).eq("is_active", True).execute())
            
            if not rep_res.data:
                # Fallback: Check if the UUID is an admins table ID
                admin_res = await db_execute(lambda: db.table("admins").select("email, full_name").eq("id", str(uuid_val)).execute())
                if admin_res.data:
                    admin_data = admin_res.data[0]
                    # First map by email
                    rep_res = await db_execute(lambda: db.table("sales_reps").select("*").eq("email", admin_data["email"]).eq("is_active", True).execute())
                    if not rep_res.data:
                        # Fallback match by name
                        rep_res = await db_execute(lambda: db.table("sales_reps").select("*").ilike("name", f"%{admin_data['full_name']}%").eq("is_active", True).execute())
                    
                    # If still no match in sales_reps, construct a visual fallback
                    if not rep_res.data:
                        rep_data = {"id": str(uuid_val), "name": admin_data["full_name"]}
        except ValueError:
            # Fallback to name search for legacy links
            normalized_rep = rep.replace("_", " ").replace("-", " ")
            rep_res = await db_execute(lambda: db.table("sales_reps").select("*").ilike("name", f"%{normalized_rep}%").eq("is_active", True).execute())
            
        if rep_res and getattr(rep_res, 'data', None):
            rep_data = rep_res.data[0]
            
    # List of active properties for the dropdown (Ensuring unique names)
    prop_res = await db_execute(lambda: db.table("properties").select("name").eq("is_active", True).execute())
    properties_list = sorted(list(set([p["name"] for p in prop_res.data if p.get("name")])))
    
    return templates.TemplateResponse("property_subscription.html", {
        "request": request,
        "rep": rep_data,
        "properties": properties_list
    })

@router.post("/api/subscriptions/submit")
async def submit_subscription(
    request: Request,
    payload: dict # Expecting JSON for most fields, files handled separately or via base64
):
    """
    Handles the multi-step form submission.
    """
    try:
        # Capture legal metadata for audit/security
        payload["ip_address"] = request.client.host
        payload["user_agent"] = request.headers.get("user-agent")

        # 1. Signature Handling (Base64 from Canvas or Uploaded Image)
        signature_base64 = payload.get("signature_data")
        invoice_temp_num = f"TEMP_{uuid.uuid4().hex[:8]}"
        
        final_sig_url = await SubscriptionService.process_signature(signature_base64, invoice_temp_num) if signature_base64 else None
        
        # 2. Add signature URL to payload
        payload["signature_url"] = final_sig_url
        
        # 2.5 Process Generic Documents if Base64 forms were passed
        if payload.get("passport_photo_b64"):
            payload["passport_photo_url"] = await SubscriptionService.process_base64_file(payload.get("passport_photo_b64"), invoice_temp_num, "passport")
            
        if payload.get("nin_document_b64"):
            payload["nin_document_url"] = await SubscriptionService.process_base64_file(payload.get("nin_document_b64"), invoice_temp_num, "nin_id")
            
        if payload.get("payment_receipt_b64"):
            payload["payment_receipt_url"] = await SubscriptionService.process_base64_file(payload.get("payment_receipt_b64"), invoice_temp_num, "receipt")
        
        # 3. Process the full land purchase workflow
        sales_rep_id = payload.get("sales_rep_id")
        result = await SubscriptionService.process_subscription(payload, sales_rep_id=sales_rep_id)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Subscription received and being processed.",
            "invoice_number": result["invoice_number"]
        })
        
    except Exception as e:
        print(f"SUBSCRIPTION SUBMISSION ERROR: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.post("/api/subscriptions/upload-file")
async def upload_subscription_file(
    file: UploadFile = File(...),
    file_type: str = Form(...) # 'passport', 'nin', 'receipt'
):
    """
    Handles immediate, background file uploads from the subscription form.
    Returns the public URL of the uploaded file.
    """
    try:
        # 1. Read file content
        content = await file.read()
        
        # 2. Extract base64 to reuse existing processing logic (normalization to PNG/PDF)
        import base64
        encoded = base64.b64encode(content).decode('utf-8')
        mime = file.content_type or "image/png"
        base64_data = f"data:{mime};base64,{encoded}"
        
        # 3. Process and upload
        temp_invoice_num = f"UP_{uuid.uuid4().hex[:6]}"
        url = await SubscriptionService.process_base64_file(base64_data, temp_invoice_num, file_type)
        
        if not url:
            raise Exception("File processing failed")
            
        return {"status": "success", "url": url}
    except Exception as e:
        print(f"ASYNC UPLOAD ERROR: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


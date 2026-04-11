from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import get_db, SUPABASE_URL
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
        try:
            # First, assume it's a unique ID (UUID)
            uuid_val = uuid.UUID(rep)
            rep_res = db.table("sales_reps").select("*").eq("id", str(uuid_val)).eq("is_active", True).execute()
        except ValueError:
            # Fallback to name search for legacy links
            normalized_rep = rep.replace("_", " ").replace("-", " ")
            rep_res = db.table("sales_reps").select("*").ilike("name", f"%{normalized_rep}%").eq("is_active", True).execute()
            
        if rep_res.data:
            rep_data = rep_res.data[0]
            
    # List of active properties for the dropdown (Ensuring unique names)
    prop_res = db.table("properties").select("name").eq("is_active", True).execute()
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
        # 1. Signature Handling (Base64 from Canvas or Uploaded Image)
        signature_base64 = payload.get("signature_data")
        invoice_temp_num = f"TEMP_{uuid.uuid4().hex[:8]}"
        
        final_sig_url = SubscriptionService.process_signature(signature_base64, invoice_temp_num) if signature_base64 else None
        
        # 2. Add signature URL to payload
        payload["signature_url"] = final_sig_url
        
        # 2.5 Process Generic Documents if Base64 forms were passed
        if payload.get("passport_photo_b64"):
            payload["passport_photo_url"] = SubscriptionService.process_base64_file(payload.get("passport_photo_b64"), invoice_temp_num, "passport")
            
        if payload.get("nin_document_b64"):
            payload["nin_document_url"] = SubscriptionService.process_base64_file(payload.get("nin_document_b64"), invoice_temp_num, "nin_id")
            
        if payload.get("payment_receipt_b64"):
            payload["payment_receipt_url"] = SubscriptionService.process_base64_file(payload.get("payment_receipt_b64"), invoice_temp_num, "receipt")
        
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


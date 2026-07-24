from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import get_db, SUPABASE_URL, db_execute
from subscription_service import SubscriptionService
import uuid
import os
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/kyc", response_class=HTMLResponse)
async def get_kyc_form(request: Request, rep: str = None, t: str = None):
    """
    Renders a simple KYC public form.
    Supports `rep` query param (UUID or name) OR `t` (KYC link token) to attribute the lead to a rep.
    """
    db = get_db()
    rep_data = None

    # --- Resolve rep from KYC link token (t=...) ---
    if t and not rep:
        try:
            token_res = await db_execute(lambda: db.table("kyc_links").select("rep_id").eq("token", t).eq("is_active", True).limit(1).execute())
            if token_res.data:
                rep = token_res.data[0]["rep_id"]  # treat resolved rep_id as the rep param
        except Exception as te:
            print(f"[KYC] Token resolve error: {te}")

    if rep:
        try:
            uuid_val = uuid.UUID(rep)
            rep_res = await db_execute(lambda: db.table("sales_reps").select("*").eq("id", str(uuid_val)).eq("is_active", True).execute())
            if rep_res.data:
                rep_data = rep_res.data[0]
            else:
                # Fallback: look up in admins table (KYC links are created by admins)
                admin_res = await db_execute(lambda: db.table("admins").select("id, full_name").eq("id", str(uuid_val)).execute())
                if admin_res.data:
                    rep_data = {"id": str(uuid_val), "name": admin_res.data[0].get("full_name")}
        except Exception:
            normalized = rep.replace("_", " ").replace("-", " ")
            rep_search = await db_execute(lambda: db.table("sales_reps").select("*").ilike("name", f"%{normalized}%").eq("is_active", True).execute())
            if rep_search.data:
                rep_data = rep_search.data[0]

    # Simple occupations list for datalist (could be extended or moved to DB)
    occupations = ["Engineer", "Accountant", "Architect", "Business Owner", "Consultant", "Doctor", "Farmer", "Lawyer", "Marketer", "Student", "Teacher"]

    return templates.TemplateResponse("kyc_form.html", {"request": request, "rep": rep_data, "occupations": occupations})


@router.post("/api/kyc/submit")
async def submit_kyc(request: Request):
    """
    Accepts JSON payload from public KYC form and creates/updates a `clients` row.
    Required: `full_name`, `email`, `phone`.
    Optional: `occupation`, `address`, `city`, `state`, `lead_source`, `rep`.
    """
    try:
        payload = await request.json()
        # Basic server-side validation
        full_name = (payload.get("full_name") or "").strip()
        email = (payload.get("email") or "").strip()
        phone = (payload.get("phone") or "").strip()

        if not full_name:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Full name is required"})
        if not email:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Email is required"})
        if not phone:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Phone is required"})

        db = get_db()

        # Resolve rep if provided (accepts UUID or name)
        rep = payload.get("rep")
        assigned_rep_id = None
        if rep:
            try:
                uuid_val = uuid.UUID(rep)
                # 1. Try sales_reps table first
                rep_res = await db_execute(lambda: db.table("sales_reps").select("id").eq("id", str(uuid_val)).eq("is_active", True).execute())
                if rep_res.data:
                    assigned_rep_id = rep_res.data[0]["id"]
                else:
                    # 2. Fallback: KYC links are tied to admin accounts, so check admins table
                    admin_res = await db_execute(lambda: db.table("admins").select("id").eq("id", str(uuid_val)).execute())
                    if admin_res.data:
                        assigned_rep_id = admin_res.data[0]["id"]
            except Exception:
                rep_search = await db_execute(lambda: db.table("sales_reps").select("id").ilike("name", f"%{rep}%").eq("is_active", True).execute())
                if rep_search.data:
                    assigned_rep_id = rep_search.data[0]["id"]

        client_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "occupation": payload.get("occupation"),
            "address": payload.get("address"),
            "city": payload.get("city"),
            "state": payload.get("state"),
            "lead_source": payload.get("lead_source") or payload.get("referral_source"),
            "client_type": "lead",
            "pipeline_stage": "lead",
            "assigned_rep_id": assigned_rep_id,
            "created_at": None
        }

        # Matching on email or phone — update if exists
        match_filters = []
        if email: match_filters.append(f"email.eq.{email}")
        if phone: match_filters.append(f"phone.eq.{phone}")

        existing = None
        if match_filters:
            match_res = await db_execute(lambda: db.table("clients").select("id").or_(",".join(match_filters)).execute())
            if match_res.data:
                existing = match_res.data[0]["id"]

        if existing:
            await db_execute(lambda: db.table("clients").update({k: v for k, v in client_data.items() if v is not None}).eq("id", existing).execute())
            client_id = existing
        else:
            import datetime
            client_data["created_at"] = datetime.datetime.utcnow().isoformat()
            insert_res = await db_execute(lambda: db.table("clients").insert(client_data).execute())
            client_id = insert_res.data[0]["id"]

        # Log activity
        try:
            await db_execute(lambda: db.table("activity_log").insert({
                "event_type": "kyc_submission",
                "description": f"Public KYC submitted by {full_name}",
                "client_id": client_id,
                "performed_by": assigned_rep_id or None,
                "metadata": {"lead_source": client_data.get("lead_source")}
            }).execute())
        except Exception:
            pass

        return JSONResponse(content={"status": "success", "client_id": client_id})
    except Exception as e:
        print(f"KYC SUBMIT ERROR: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


async def _notify_lawyers_subscription(client_name: str, property_name: str, invoice_number: str):
    """
    Fire a legal_notifications row for every admin whose role includes
    'lawyer' or 'legal' when a new subscription form is submitted.
    Non-critical — all errors are swallowed.
    """
    try:
        db = get_db()
        lawyers_res = await db_execute(
            lambda: db.table("admins")
                .select("id, role")
                .eq("is_active", True)
                .execute()
        )
        for admin in (lawyers_res.data or []):
            roles = {r.strip().lower() for r in (admin.get("role") or "").split(",")}
            if roles & {"lawyer", "legal", "super_admin", "admin"}:
                try:
                    await db_execute(lambda: db.table("legal_notifications").insert({
                        "recipient_id": admin["id"],
                        "type": "subscription",
                        "title": f"📝 New subscription form — {property_name or 'Property'}",
                        "message": f"{client_name or 'A prospect'} submitted a subscription form. Invoice: {invoice_number}.",
                    }).execute())
                except Exception:
                    pass
    except Exception as _e:
        print(f"[LegalNotif] subscription notify error: {_e}")


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
            
    # List of active properties for the dropdown (Ensuring clean, unique names)
    prop_res = await db_execute(lambda: db.table("properties").select("name, estate_name").eq("is_active", True).execute())
    
    unique_names = set()
    for p in prop_res.data:
        # Use estate_name if it exists, otherwise clean up the name
        e_name = p.get("estate_name")
        if not e_name:
            p_name = p.get("name", "")
            # Strip suffixes to get the clean base name
            e_name = p_name
            for suffix in [" - ", " (Outright)", " (Installment)", " (Outright Payment)", " (Installment Payment)"]:
                if suffix in e_name:
                    e_name = e_name.split(suffix)[0]
                    break
        
        if e_name:
            unique_names.add(e_name.strip())
            
    properties_list = sorted(list(unique_names))
    
    return templates.TemplateResponse("property_subscription.html", {
        "request": request,
        "rep": rep_data,
        "properties": properties_list
    })


@router.get('/kyc-success', response_class=HTMLResponse)
async def kyc_success(request: Request):
    return templates.TemplateResponse('kyc_success.html', {"request": request})

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

        # Multi-file receipt: front-end sends payment_receipt_urls as a list.
        # Serialise to a JSON string so the single DB column stores all paths.
        if payload.get("payment_receipt_urls"):
            import json as _json
            urls = payload["payment_receipt_urls"]
            if isinstance(urls, list) and len(urls) > 0:
                # Store JSON array; keep legacy field pointing to the first URL
                payload["payment_receipt_url"] = _json.dumps(urls)
        
        # 3. Process the full land purchase workflow
        sales_rep_id = payload.get("sales_rep_id")
        result = await SubscriptionService.process_subscription(payload, sales_rep_id=sales_rep_id)
        
        # ── Legal notification: new subscription form submitted ──
        try:
            client_name   = payload.get("full_name") or payload.get("name") or "A prospect"
            property_name = payload.get("property_name") or payload.get("property") or "Property"
            await _notify_lawyers_subscription(client_name, property_name, result["invoice_number"])
        except Exception as _ne:
            print(f"[LegalNotif] subscription post-notify error: {_ne}")

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


@router.get('/api/occupations')
async def search_occupations(q: str = None):
    """Return a short list of occupations matching the query."""
    try:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        data_path = os.path.join(base, 'data', 'occupations.json')
        if not os.path.exists(data_path):
            return JSONResponse(content=[], status_code=200)
        with open(data_path, 'r', encoding='utf-8') as fh:
            occs = json.load(fh)
        if not q:
            # return popular/top alphabetic subset
            return JSONResponse(content=occs[:60])
        qlow = q.strip().lower()
        matches = [o for o in occs if qlow in o.lower()]
        return JSONResponse(content=matches[:60])
    except Exception as e:
        print(f"Occupations search error: {e}")
        return JSONResponse(content=[], status_code=500)
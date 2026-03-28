from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from models import WebhookFormPayload
from database import get_db, SUPABASE_URL
import os
import base64
import io
from PIL import Image
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass
from datetime import date, timedelta
from email_service import send_invoice_email, send_admin_alert_email, send_welcome_email
from routers.analytics import log_activity
from utils import calculate_due_date

router = APIRouter()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

@router.post("/form-submission")
async def form_submission(
    payload: WebhookFormPayload,
    request: Request,
    background_tasks: BackgroundTasks
):
    # 1. Validate secret
    secret = request.headers.get("X-Webhook-Secret")
    if not WEBHOOK_SECRET or secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # 2. Validate consent
    # Basic verification: ensure the user at least checked the consent box
    consent_text = (payload.consent or "").lower()
    if "confirm" not in consent_text and "agree" not in consent_text:
        print(f"DEBUG: Skipping form due to missing consent: {payload.consent}")
        return {"status": "ignored", "message": "Consent not confirmed"}

    db = get_db()

    try:
        # 3. Upsert client
        full_name = f"{payload.first_name} {payload.middle_name + ' ' if payload.middle_name else ''}{payload.last_name}".strip()
        client_data = {
            "full_name": full_name,
            "email": payload.email,
            "phone": payload.phone,
            "address": payload.address,
            "city": payload.city,
            "state": payload.state,
            "title": payload.title,
            "middle_name": payload.middle_name,
            "gender": payload.gender,
            "dob": payload.dob,
            "marital_status": payload.marital_status,
            "occupation": payload.occupation,
            "nin": payload.nin,
            "id_number": payload.id_number,
            "id_document_url": payload.id_document_url,
            "nationality": payload.nationality,
            "passport_photo_url": payload.passport_photo_url,
            "nok_name": payload.nok_name,
            "nok_phone": payload.nok_phone,
            "nok_email": payload.nok_email,
            "nok_occupation": payload.nok_occupation,
            "nok_relationship": payload.nok_relationship,
            "nok_address": payload.nok_address,
            "source_of_income": payload.source_of_income,
            "referral_source": payload.referral_source,
        }

        # Search by email
        client_res = db.table("clients").select("*").eq("email", payload.email).execute()
        if client_res.data:
            client_id = client_res.data[0]["id"]
            db.table("clients").update(jsonable_encoder(client_data)).eq("id", client_id).execute()
        else:
            new_client = db.table("clients").insert(jsonable_encoder(client_data)).execute()
            client_id = new_client.data[0]["id"]

        # 4. Sales Rep Detection
        rep_name_to_use = payload.sales_rep_name
        sales_rep_id_to_use = None
        matched_rep = None

        if payload.sales_rep_phone or payload.sales_rep_name:
            # Phase 1: Try Phone Match (Normalized)
            if payload.sales_rep_phone:
                import re
                cleaned_phone = re.sub(r'\D', '', payload.sales_rep_phone)
                # Normalize (assuming Nigerian numbers: strip '234' or leading '0')
                if cleaned_phone.startswith('234') and len(cleaned_phone) > 10:
                    cleaned_phone = cleaned_phone[3:]
                elif cleaned_phone.startswith('0') and len(cleaned_phone) == 11:
                    cleaned_phone = cleaned_phone[1:]
                
                if len(cleaned_phone) >= 7: # Safety check
                    rep_res = db.table("sales_reps").select("*").ilike("phone", f"%{cleaned_phone}%").eq("is_active", True).execute()
                    if rep_res.data:
                        matched_rep = rep_res.data[0] # Take first match for phone
            
            # Phase 2: Try Exact Name Match
            if not matched_rep and payload.sales_rep_name:
                rep_res = db.table("sales_reps").select("*").eq("name", payload.sales_rep_name).eq("is_active", True).execute()
                if rep_res.data:
                    matched_rep = rep_res.data[0]
            
            # Phase 3: Try Partial Name Match (ONLY if single result found)
            if not matched_rep and payload.sales_rep_name:
                rep_res = db.table("sales_reps").select("*").ilike("name", f"%{payload.sales_rep_name}%").eq("is_active", True).execute()
                # Use ONLY if exactly one match found to prevent wrong commission assignment
                if len(rep_res.data) == 1:
                    matched_rep = rep_res.data[0]
            
            if matched_rep:
                rep_name_to_use = matched_rep["name"]
                sales_rep_id_to_use = matched_rep["id"]
            else:
                # Log as unmatched if we have a name/phone but no clear DB match
                name_to_log = payload.sales_rep_name or f"Phone: {payload.sales_rep_phone}"
                unmatched_res = db.table("unmatched_reps").select("*").eq("name_from_form", name_to_log).execute()
                if unmatched_res.data:
                    db.table("unmatched_reps").update({
                        "times_seen": unmatched_res.data[0]["times_seen"] + 1,
                        "last_seen": "now()"
                    }).eq("id", unmatched_res.data[0]["id"]).execute()
                else:
                    db.table("unmatched_reps").insert({"name_from_form": name_to_log}).execute()

        # 5. Create invoice
        # Generate invoice number via DB function
        seq_result = db.rpc("generate_invoice_number").execute()
        invoice_number = seq_result.data

        # Parse plot size sqm if possible (strip non-numeric except dot)
        import re
        plot_size_numeric = None
        if payload.plot_size:
            cleaned_size = re.sub(r'[^\d.]+', '', payload.plot_size)
            if cleaned_size:
                try: plot_size_numeric = float(cleaned_size)
                except: pass

        # Quantity (default to 1)
        quantity_to_use = payload.quantity if payload.quantity > 0 else 1

        # Dates
        invoice_date = date.today()
        # Calculate due date based on payment duration (installment)
        due_date_str = calculate_due_date(
            payment_date_str=payload.payment_date or str(invoice_date),
            payment_duration=payload.payment_duration
        )

        # 5. Get Property Price from DB
        # If not provided in form, lookup by name and exact size
        total_amount_to_use = payload.total_amount
        property_location_to_use = None
        property_id_to_use = None

        if payload.property_name:
            query = db.table("properties").select("id, total_price, price_per_sqm, location")\
                .ilike("name", f"%{payload.property_name}%")\
                .eq("is_active", True)
            
            # Filter by exact plot size if we parsed one
            if plot_size_numeric:
                query = query.eq("plot_size_sqm", plot_size_numeric)
            
            prop_res = query.execute()
            
            if prop_res.data:
                prop = prop_res.data[0]
                property_id_to_use = prop.get("id")
                property_location_to_use = prop.get("location")
                
                # Determine Unit Price
                unit_price = 0
                if prop.get("starting_price") and float(prop.get("starting_price")) > 0:
                    unit_price = float(prop.get("starting_price"))
                elif prop.get("price_per_sqm") and plot_size_numeric:
                    unit_price = float(prop.get("price_per_sqm")) * plot_size_numeric
                
                # Auto-calculate total amount if not provided or set to 0
                if total_amount_to_use <= 0 and unit_price > 0:
                    total_amount_to_use = unit_price * quantity_to_use
                
                print(f"DEBUG: Found property {payload.property_name} (ID: {property_id_to_use}, Unit Price: {unit_price})")

        # 5. Handle Signature Storage
        signature_url_to_save = payload.signature_url
        if payload.signature_base64:
            try:
                # 1. Parse MIME and data
                if "," in payload.signature_base64:
                    header, encoded = payload.signature_base64.split(",", 1)
                    mime = header.split("data:")[1].split(";")[0] if "data:" in header else "image/png"
                else:
                    encoded = payload.signature_base64
                    mime = "image/png"
                
                ext = mime.split("/")[1] if "/" in mime else "png"
                img_data = base64.b64decode(encoded)
                
                # --- CONVERSION STEP: Force to PNG for PDF compatibility ---
                try:
                    with Image.open(io.BytesIO(img_data)) as img:
                        # Convert to RGBA (keeps transparency) or RGB if needed
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                        
                        out_buf = io.BytesIO()
                        img.save(out_buf, format="PNG")
                        img_data = out_buf.getvalue()
                        mime = "image/png"
                        ext = "png"
                except Exception as img_err:
                    print(f"WARNING: Image conversion failed, uploading as-is: {img_err}")
                
                # 2. Upload to storage
                file_path = f"customer_signatures/sig_{invoice_number}.{ext}"
                # Use the storage client from db
                db.storage.from_("signatures").upload(
                    path=file_path, 
                    file=img_data, 
                    file_options={"content-type": mime, "upsert": "true"}
                )
                
                # 3. Build public URL
                signature_url_to_save = f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
                print(f"DEBUG: Signature uploaded to {signature_url_to_save}")
            except Exception as e:
                print(f"ERROR: Signature upload to storage failed: {e}")
                # Fallback to saving base64 if upload fails
                signature_url_to_save = payload.signature_base64

        invoice_insert = {
            "invoice_number": invoice_number,
            "client_id": client_id,
            "property_id": property_id_to_use,
            "property_name": payload.property_name,
            "property_location": property_location_to_use,
            "plot_size_sqm": plot_size_numeric,
            "unit_price": unit_price if 'unit_price' in locals() else None,
            "amount": total_amount_to_use,
            "amount_paid": payload.deposit_amount,
            "quantity": quantity_to_use,
            "payment_terms": payload.payment_terms,
            "invoice_date": str(invoice_date),
            "due_date": due_date_str,
            "sales_rep_name": rep_name_to_use,
            "sales_rep_id": sales_rep_id_to_use,
            "co_owner_name": payload.co_owner_name,
            "co_owner_email": payload.co_owner_email,
            "signature_url": signature_url_to_save,
            "payment_proof_url": payload.payment_proof_url,
            "passport_photo_url": payload.passport_photo_url,
            "purchase_purpose": payload.purchase_purpose,
            "source": "google_form"
        }

        invoice_res = db.table("invoices").insert(jsonable_encoder(invoice_insert)).execute()
        invoice = invoice_res.data[0]

        # 5. Record deposit payment
        if payload.deposit_amount > 0:
            print(f"DEBUG: Inserting payment for {payload.deposit_amount}")
            payment_data = {
                "invoice_id": invoice["id"],
                "client_id": client_id,
                "reference": f"{payload.payment_date or str(invoice_date)}_form_deposit",
                "amount": payload.deposit_amount,
                "payment_method": "Bank Transfer", # Default for form
                "payment_date": payload.payment_date or str(invoice_date),
                "notes": "Initial deposit via subscription form"
            }
            db.table("payments").insert(jsonable_encoder(payment_data)).execute()

        # 6. Create pending verification
        verify_data = {
            "invoice_id": invoice["id"],
            "client_id": client_id,
            "payment_proof_url": payload.payment_proof_url,
            "deposit_amount": payload.deposit_amount,
            "payment_date": payload.payment_date,
            "sales_rep_name": rep_name_to_use,
            "status": "pending"
        }
        db.table("pending_verifications").insert(jsonable_encoder(verify_data)).execute()

        # 7. Emails
        # Fetch full client data for email (with nested info if needed)
        full_client = db.table("clients").select("*").eq("id", client_id).execute().data[0]
        
        background_tasks.add_task(send_welcome_email, full_client, payload.property_name)
        background_tasks.add_task(send_admin_alert_email, invoice, full_client)
        
        background_tasks.add_task(
            log_activity,
            "form_submission",
            f"New subscription for {full_name} via Google Form",
            "system", # Webhook is system-triggered
            client_id=client_id,
            invoice_id=invoice["id"]
        )

        return {
            "message": "Processed successfully",
            "invoice_number": invoice_number,
            "client_id": client_id
        }

    except Exception as e:
        print(f"WEBHOOK ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error processing webhook: {str(e)}")

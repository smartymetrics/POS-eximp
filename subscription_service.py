import os
import base64
import io
import re
from datetime import date, datetime
from typing import Optional
from PIL import Image
from fastapi.encoders import jsonable_encoder
from database import get_db, SUPABASE_URL, db_execute
from email_service import send_admin_alert_email, send_welcome_email
from marketing_logic import sync_client_to_marketing

class SubscriptionService:
    @staticmethod
    async def process_subscription(data: dict, sales_rep_id: Optional[str] = None):
        """
        The central engine for land purchases. 
        Mirrors the Google Form workflow but with better error handling and RLS.
        """
        db = get_db()
        
        # 1. Upsert Client
        email = data.get("email", "").strip().lower()
        full_name = f"{data.get('first_name', '')} {data.get('middle_name', '') + ' ' if data.get('middle_name') else ''}{data.get('last_name', '')}".strip()
        
        # Intelligent Mapping for Form Parity
        id_number = data.get("nin_id_number") or data.get("id_number")
        id_doc_url = data.get("nin_document_url") or data.get("id_document_url") or data.get("international_passport_url")
        phone = data.get("whatsapp_phone") or data.get("phone")

        client_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "address": data.get("residential_address") or data.get("address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "title": data.get("title"),
            "gender": data.get("gender"),
            "dob": data.get("date_of_birth") or data.get("dob"),
            "marital_status": data.get("marital_status"),
            "occupation": data.get("occupation"),
            "nin": id_number,
            "nationality": data.get("nationality", "Nigerian"),
            "passport_photo_url": data.get("passport_photo_url"),
            "id_document_url": id_doc_url,
            "nok_name": data.get("nok_full_name") or data.get("nok_name"),
            "nok_phone": data.get("nok_phone"),
            "nok_email": data.get("nok_email"),
            "nok_occupation": data.get("nok_occupation"),
            "nok_relationship": data.get("nok_relationship"),
            "nok_address": data.get("nok_address"),
            "source_of_income": data.get("source_of_income"),
            "referral_source": data.get("referral_source"),
        }

        # Check existing
        client_res = await db_execute(lambda: db.table("clients").select("id").eq("email", email).execute())
        if client_res.data:
            client_id = client_res.data[0]["id"]
            await db_execute(lambda: db.table("clients").update(jsonable_encoder(client_data)).eq("id", client_id).execute())
        else:
            new_client = await db_execute(lambda: db.table("clients").insert(jsonable_encoder(client_data)).execute())
            client_id = new_client.data[0]["id"]

        # 2. Resolve Sales Rep for Commission Tracking
        final_sales_rep_id = sales_rep_id if sales_rep_id and str(sales_rep_id).strip() else None
        final_sales_rep_name = None
        
        if final_sales_rep_id:
            rep_res = await db_execute(lambda: db.table("sales_reps").select("name").eq("id", final_sales_rep_id).execute())
            if rep_res.data:
                final_sales_rep_name = rep_res.data[0]["name"]
        elif data.get("sales_rep_name"):
            # Fallback to name search if ID not provided (manual entry)
            rep_res = await db_execute(lambda: db.table("sales_reps").select("id, name").eq("name", data["sales_rep_name"]).execute())
            if rep_res.data:
                final_sales_rep_id = rep_res.data[0]["id"]
                final_sales_rep_name = rep_res.data[0]["name"]
            else:
                final_sales_rep_name = data["sales_rep_name"]

        # 3. Generate Invoice Number
        invoice_number = (await db_execute(lambda: db.rpc("generate_invoice_number").execute())).data

        # 4. Property Matching & Numeric Casting
        property_id = None
        property_location = None
        
        # Explicitly cast form strings to numbers
        try:
            total_amount = float(data.get("total_amount") or 0)
            deposit_amount = float(data.get("deposit_amount") or 0)
            quantity = int(data.get("quantity") or 1)
        except (ValueError, TypeError):
            total_amount = 0
            deposit_amount = 0
            quantity = 1
        
        if data.get("property_name"):
            # Try to handle plot size matching (e.g. "500sqm" -> 500)
            plot_size_str = data.get("plot_size", "")
            size_match = re.search(r'(\d+)', plot_size_str)
            target_size = float(size_match.group(1)) if size_match else None

            prop_query = db.table("properties").select("*").ilike("name", f"%{data['property_name']}%").eq("is_active", True)
            prop_res = await db_execute(lambda: prop_query.execute())
            
            if prop_res.data:
                # Find best match based on plot size if available
                prop = prop_res.data[0] # Default to first
                if target_size:
                    for p in prop_res.data:
                        p_size = float(p.get("plot_size_sqm") or 0)
                        if abs(p_size - target_size) < 1: # Close enough match
                            prop = p
                            break
                
                property_id = prop["id"]
                property_location = prop.get("location")
                
                if total_amount <= 0:
                    # Priority order for price columns based on user database feedback
                    unit_price = float(prop.get("total_price") or prop.get("starting_price") or prop.get("price_per_sqm") or 0)
                    total_amount = unit_price * quantity

        # 5. Create Invoice record
        invoice_insert = {
            "invoice_number": invoice_number,
            "client_id": client_id,
            "property_id": property_id,
            "property_name": data.get("property_name"),
            "property_location": property_location,
            "amount": total_amount,
            "amount_paid": deposit_amount,
            "payment_terms": data.get("payment_duration", "Outright"),
            "invoice_date": str(date.today()),
            "due_date": str(date.today()), # Default
            "sales_rep_id": final_sales_rep_id,
            "sales_rep_name": final_sales_rep_name,
            "co_owner_name": data.get("co_owner_name"),
            "co_owner_email": data.get("co_owner_email"),
            "signature_url": data.get("signature_url"),
            "payment_proof_url": data.get("payment_receipt_url"),
            "source": "custom_portal",
            "pipeline_stage": "inspection"
        }
        
        inv_res = await db_execute(lambda: db.table("invoices").insert(jsonable_encoder(invoice_insert)).execute())
        invoice_id = inv_res.data[0]["id"]

        # 6. Save raw subscription for audit/metadata
        # Strict Whitelist Filtering to prevent PGRST204 Schema Errors
        ALLOWED_SUB_COLUMNS = {
            'sales_rep_id', 'status', 'title', 'first_name', 'last_name', 'middle_name', 
            'gender', 'date_of_birth', 'residential_address', 'email', 'whatsapp_phone', 
            'marital_status', 'occupation', 'nationality', 'passport_photo_url', 
            'nin_id_number', 'nin_document_url', 'international_passport_url', 
            'property_name', 'plot_size', 'ownership_type', 'purchase_purpose', 
            'nok_full_name', 'nok_phone', 'nok_email', 'nok_occupation', 'nok_relationship', 
            'nok_address', 'co_owner_name', 'co_owner_address', 'co_owner_occupation', 
            'co_owner_phone', 'co_owner_email', 'payment_duration', 'deposit_amount', 
            'payment_date', 'payment_receipt_url', 'source_of_income', 
            'referral_source', 'signature_url', 'consent_given', 'consented_at', 
            'ip_address', 'user_agent', 'city', 'state', 'phone', 'quantity', 
            'total_amount', 'sales_rep_name', 'utm_source', 'utm_medium', 
            'utm_campaign', 'utm_content', 'utm_term'
        }

        subscription_record = {
            "sales_rep_id": final_sales_rep_id, 
            "status": "processed",
            "date_of_birth": data.get("date_of_birth") or data.get("dob"),
            "nin_id_number": data.get("nin_id_number") or data.get("id_number"),
            "nin_document_url": data.get("nin_document_url") or data.get("id_document_url")
        }
        
        # Add all valid incoming data to the record
        for key, value in data.items():
            if key in ALLOWED_SUB_COLUMNS and key not in subscription_record:
                subscription_record[key] = value

        sub_res = await db_execute(lambda: db.table("property_subscriptions").insert(jsonable_encoder(subscription_record)).execute())
        subscription_id = sub_res.data[0]["id"] if sub_res.data else None

        # 7. Create Pending Verification for Admin
        if deposit_amount > 0:
            verify_data = {
                "invoice_id": invoice_id,
                "client_id": client_id,
                "subscription_id": subscription_id,
                "payment_proof_url": data.get("payment_receipt_url"),
                "deposit_amount": deposit_amount,
                "payment_date": data.get("payment_date"),
                "sales_rep_name": final_sales_rep_name,
                "status": "pending"
            }
            await db_execute(lambda: db.table("pending_verifications").insert(jsonable_encoder(verify_data)).execute())

        # 8. Notifications & Marketing Sync
        try:
            full_client_res = await db_execute(lambda: db.table("clients").select("*").eq("id", client_id).execute())
            full_client = full_client_res.data[0]
            
            # --- INTELLIGENT ATTRIBUTION LOOK-BACK ---
            # If no campaign was provided by the form, try to find the last one from marketing_contacts
            current_mcid = data.get("marketing_campaign_id") or data.get("mcid")
            if not current_mcid or not str(current_mcid).strip():
                current_mcid = None
                mc_attr = await db_execute(lambda: db.table("marketing_contacts").select("last_campaign_id").eq("email", email).execute())
                if mc_attr.data and mc_attr.data[0].get("last_campaign_id"):
                    current_mcid = mc_attr.data[0]["last_campaign_id"]
            
            # Final safety check for UUID format
            if current_mcid and not str(current_mcid).strip():
                current_mcid = None
            
            # Update invoice with attribution if found
            if current_mcid:
                await db_execute(lambda: db.table("invoices").update({"marketing_campaign_id": current_mcid}).eq("id", invoice_id).execute())

            await send_welcome_email(full_client, data.get("property_name"))
            
            invoice = inv_res.data[0]
            await send_admin_alert_email(invoice, full_client)
            await sync_client_to_marketing(full_client)
        except Exception as e:
            print(f"Post-submission notification failed: {e}")

        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "client_id": client_id
        }

    @staticmethod
    async def process_signature(base64_data: str, invoice_number: str) -> Optional[str]:
        """Converts base64 signature to PNG and uploads to Supabase Storage."""
        if not base64_data or not base64_data.startswith("data:"):
            return None
            
        db = get_db()
        try:
            header, encoded = base64_data.split(",", 1)
            img_data = base64.b64decode(encoded)
            
            with Image.open(io.BytesIO(img_data)) as img:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                out_buf = io.BytesIO()
                img.save(out_buf, format="PNG")
                img_data = out_buf.getvalue()

            file_path = f"customer_signatures/sig_{invoice_number}.png"
            await db_execute(lambda: db.storage.from_("signatures").upload(
                path=file_path,
                file=img_data,
                file_options={"content-type": "image/png", "upsert": "true"}
            ))
            return f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
        except Exception as e:
            print(f"Signature upload failed: {e}")
            return None

    @staticmethod
    async def process_base64_file(base64_data: str, invoice_number: str, file_type: str) -> Optional[str]:
        """Uploads base64 document (image or PDF) to Supabase Storage."""
        if not base64_data or not base64_data.startswith("data:"):
            return None
            
        db = get_db()
        try:
            head, encoded = base64_data.split(",", 1)
            raw_bytes = base64.b64decode(encoded)
            
            # Detect MIME type and validate against strict whitelist
            ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
            mime_type = head.split(":")[1].split(";")[0] if ":" in head and ";" in head else "image/png"
            
            if mime_type not in ALLOWED_MIME_TYPES:
                print(f"REJECTED: Unsupported file type detected: {mime_type}")
                return None
            
            if mime_type == "application/pdf":
                # Upload PDF directly — skip PIL entirely
                file_path = f"client_documents/{invoice_number}_{file_type}.pdf"
                await db_execute(lambda: db.storage.from_("signatures").upload(
                    path=file_path,
                    file=raw_bytes,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                ))
                return f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
            else:
                # It's an image — normalize to PNG via PIL
                with Image.open(io.BytesIO(raw_bytes)) as img:
                    if img.mode not in ('RGBA', 'RGB'):
                        img = img.convert('RGB')
                    out_buf = io.BytesIO()
                    img.save(out_buf, format="PNG")
                    img_data = out_buf.getvalue()

                file_path = f"client_documents/{invoice_number}_{file_type}.png"
                await db_execute(lambda: db.storage.from_("signatures").upload(
                    path=file_path,
                    file=img_data,
                    file_options={"content-type": "image/png", "upsert": "true"}
                ))
                return f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"

        except Exception as e:
            print(f"Document upload failed for {file_type}: {e}")
            return None

import base64
import os
import io
import requests
from PIL import Image
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass
from database import supabase, SUPABASE_URL

def migrate_signatures():
    print("🚀 Starting signature migration to Supabase Storage...")
    
    # 1. Fetch invoices with potentially base64 signatures
    # We look for long strings or data uris in signature_url
    res = supabase.table("invoices").select("id, invoice_number, signature_url").execute()
    
    count = 0
    for inv in res.data:
        url = inv.get("signature_url")
        if not url:
            continue
            
        # Detection logic
        is_base64 = url.startswith("data:image") or (len(url) > 500 and "http" not in url)
        is_incompatible_url = (".heic" in url.lower() or ".heif" in url.lower()) and "supabase" in url
        
        if is_base64 or is_incompatible_url:
            try:
                img_data = None
                mime = "image/png"
                
                if is_base64:
                    # Parse MIME and data from base64
                    if "," in url:
                        header, encoded = url.split(",", 1)
                        mime = header.split("data:")[1].split(";")[0] if "data:" in header else "image/png"
                    else:
                        encoded = url
                        mime = "image/png"
                    img_data = base64.b64decode(encoded)
                else:
                    # Download from URL
                    print(f"Downloading incompatible image: {url}")
                    resp = requests.get(url)
                    if resp.ok:
                        img_data = resp.content
                        mime = resp.headers.get("Content-Type", "image/heic")
                
                if not img_data:
                    continue

                # --- CONVERSION STEP: Force to PNG ---
                try:
                    with Image.open(io.BytesIO(img_data)) as img:
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                        out_buf = io.BytesIO()
                        img.save(out_buf, format="PNG")
                        img_data = out_buf.getvalue()
                        mime = "image/png"
                except Exception as img_err:
                    print(f"⚠️  Conversion failed for {inv['invoice_number']}: {img_err}")
                    if is_incompatible_url: continue # Don't update DB if we can't fix the URL

                # 2. Upload to storage
                file_path = f"customer_signatures/sig_{inv['invoice_number']}.png"
                print(f"Uploading {file_path}...")
                
                try:
                    supabase.storage.from_("signatures").remove([file_path])
                except Exception:
                    pass
                supabase.storage.from_("signatures").upload(
                    path=file_path,
                    file=img_data,
                    file_options={"content-type": "image/png"}
                )
                
                # 3. Update DB with NEW public URL
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
                supabase.table("invoices").update({"signature_url": public_url}).eq("id", inv["id"]).execute()
                
                print(f"✅ Migrated/Fixed invoice {inv['invoice_number']}")
                count += 1
                
            except Exception as e:
                print(f"❌ Failed to process {inv['invoice_number']}: {e}")
                
    print(f"\n🎉 Migration complete! {count} signatures moved to storage.")

if __name__ == "__main__":
    migrate_signatures()

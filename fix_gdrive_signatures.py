import base64
import os
import io
import requests
from PIL import Image
from database import supabase, SUPABASE_URL
from pdf_service import _get_google_drive_direct_link

def fix_gdrive_signatures():
    print("🚀 Starting GDrive to Supabase signature migration...")
    
    # Fetch all invoices
    res = supabase.table("invoices").select("id, invoice_number, signature_url").execute()
    
    count = 0
    for inv in res.data:
        url = inv.get("signature_url")
        if not url or "drive.google.com" not in url:
            continue
            
        print(f"🔄 Processing invoice {inv['invoice_number']} with GDrive link...")
        
        try:
            # 1. Get direct link and download
            direct_url = _get_google_drive_direct_link(url)
            resp = requests.get(direct_url, timeout=20)
            
            content_type = resp.headers.get("Content-Type", "")
            
            # If thumbnail fails, try the export method as fallback
            if not resp.ok or not content_type.startswith("image/"):
                file_id = None
                if "id=" in url: file_id = url.split("id=")[1].split("&")[0]
                elif "/file/d/" in url: file_id = url.split("/file/d/")[1].split("/")[0]
                
                if file_id:
                    fallback_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                    print(f"  ⚠️ Thumbnail failed (got {content_type}), trying fallback: {fallback_url}")
                    resp = requests.get(fallback_url, timeout=20)
                    content_type = resp.headers.get("Content-Type", "")

            if not resp.ok or not content_type.startswith("image/"):
                print(f"❌ Failed to get image from GDrive (got {content_type}): {url}")
                continue
                
            img_data = resp.content
            
            # 2. Conversion Step: Force to PNG
            try:
                with Image.open(io.BytesIO(img_data)) as img:
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    out_buf = io.BytesIO()
                    img.save(out_buf, format="PNG")
                    img_data = out_buf.getvalue()
            except Exception as img_err:
                print(f"⚠️  Image conversion failed: {img_err}")
                continue

            # 3. Upload to Supabase Storage
            # Following the pattern: customer_signatures/sig_{invoice_number}.png
            file_path = f"customer_signatures/sig_{inv['invoice_number']}.png"
            
            try:
                supabase.storage.from_("signatures").remove([file_path])
            except Exception:
                pass
            supabase.storage.from_("signatures").upload(
                path=file_path,
                file=img_data,
                file_options={"content-type": "image/png"}
            )
            
            # 4. Update DB with NEW public URL
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
            supabase.table("invoices").update({"signature_url": public_url}).eq("id", inv["id"]).execute()
            
            print(f"✅ Migrated invoice {inv['invoice_number']} to Supabase.")
            count += 1
            
        except Exception as e:
            print(f"❌ Unexpected error for {inv['invoice_number']}: {e}")
            
    print(f"\n🎉 Migration complete! {count} GDrive signatures moved to Supabase.")

if __name__ == "__main__":
    fix_gdrive_signatures()

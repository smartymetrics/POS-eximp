import base64
import os
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
            
        # Basic check: is it a base64 Data URI or a raw base64 string?
        is_base64 = url.startswith("data:image") or (len(url) > 500 and "http" not in url)
        
        if is_base64:
            try:
                # Parse MIME and data
                if "," in url:
                    header, encoded = url.split(",", 1)
                    mime = header.split("data:")[1].split(";")[0] if "data:" in header else "image/png"
                else:
                    encoded = url
                    mime = "image/png"
                
                ext = mime.split("/")[1] if "/" in mime else "png"
                img_data = base64.b64decode(encoded)
                
                # 2. Upload to storage
                file_path = f"customer_signatures/sig_{inv['invoice_number']}.{ext}"
                print(f"Uploading {file_path}...")
                
                supabase.storage.from_("signatures").upload(
                    path=file_path,
                    file=img_data,
                    file_options={"content-type": mime, "upsert": "true"}
                )
                
                # 3. Update DB with public URL
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/signatures/{file_path}"
                supabase.table("invoices").update({"signature_url": public_url}).eq("id", inv["id"]).execute()
                
                print(f"✅ Migrated invoice {inv['invoice_number']}")
                count += 1
                
            except Exception as e:
                print(f"❌ Failed to migrate {inv['invoice_number']}: {e}")
                
    print(f"\n🎉 Migration complete! {count} signatures moved to storage.")

if __name__ == "__main__":
    migrate_signatures()

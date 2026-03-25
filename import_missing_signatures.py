import csv
import os
from database import supabase

def backfill_signatures_from_csv():
    csv_file = "google_form_responses.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return

    print(f"🚀 Starting signature backfill from {csv_file}...")
    
    # We'll map emails to signatures from the CSV
    csv_signatures = {}
    
    try:
        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader) # skip header
            
            # Based on manual inspection:
            # Col 10 (index 10) is "Client's email address" (sometimes Col 1 or 11 depending on wrap)
            # Col 31 (index 30/31) is "Upload Signature"
            # Let's try to find them by name if indices are tricky
            
            email_idx = 10
            sig_idx = 30 # Standard index for "Upload Signature" in this CSV
            
            for row in reader:
                if len(row) < 32: continue
                email = row[email_idx].strip().lower()
                sig_url = row[sig_idx].strip()
                
                if email and sig_url and "drive.google.com" in sig_url:
                    csv_signatures[email] = sig_url
                    
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    print(f"📊 Found {len(csv_signatures)} signatures in CSV.")

    # Now update the database
    # We'll fetch all invoices to match by client email
    res = supabase.table("invoices").select("id, signature_url, clients(email)").execute()
    
    update_count = 0
    for inv in res.data:
        # Check if signature is missing
        if inv.get("signature_url"):
            continue
            
        client_email = inv.get("clients", {}).get("email", "").lower()
        if client_email in csv_signatures:
            sig_url = csv_signatures[client_email]
            print(f"✍️  Found missing signature for {client_email}. Updating...")
            
            supabase.table("invoices").update({"signature_url": sig_url}).eq("id", inv["id"]).execute()
            update_count += 1
            
    print(f"\n🎉 Backfill complete! {update_count} missing signatures added to database.")
    print("👉 Now run 'python fix_gdrive_signatures.py' to move these to Supabase.")

if __name__ == "__main__":
    backfill_signatures_from_csv()

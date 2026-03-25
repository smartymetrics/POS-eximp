import csv
import sys
from database import get_db
from dotenv import load_dotenv

load_dotenv()

# The expected CSV file path
CSV_FILE = "google_form_responses.csv"

def get_val(row, keys):
    """Helper to extract the first matching key from a CSV row."""
    for key in keys:
        if key in row and row[key].strip():
            return row[key].strip()
    return ""

def main():
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"ERROR: Could not find '{CSV_FILE}'.")
        print("Please export your Google Form responses as CSV, rename it to 'google_form_responses.csv', and place it in this folder.")
        sys.exit(1)

    db = get_db()
    print(f"Successfully loaded {len(rows)} responses from CSV.")
    
    clients_updated = 0
    invoices_updated = 0

    for idx, row in enumerate(rows):
        print(f"\n--- Processing Row {idx + 1} ---")
        
        # 1. Extract Client Identifying Info
        email = get_val(row, ["Email Address", "Client's email address", "Email"])
        first_name = get_val(row, ["Customer first name", "First Name"])
        last_name = get_val(row, ["Customer last name (surname)", "Last Name"])
        middle_name = get_val(row, ["Customer middle name", "Middle Name"])
        
        full_name = f"{first_name} {middle_name + ' ' if middle_name else ''}{last_name}".strip()
        
        if not email and not full_name:
            print("Skipping: No email or name found in row.")
            continue

        # 2. Extract All Potential Missing Client Data
        client_updates = {}
        
        # Map Google Form fields to Database Columns
        mapping_client = {
            "title": ["Title"],
            "gender": ["Gender"],
            "dob": ["Date of Birth"],
            "address": ["Client's residential address", "Residential Address"],
            "city": ["City"],
            "state": ["State"],
            "phone": ["Client's phone number\n(Whatsapp line)", "Phone Number"],
            "marital_status": ["Marital Status"],
            "occupation": ["Occupation"],
            "nationality": ["Nationality"],
            "id_number": ["International Passport No/NIN Number", "ID Card Number"],
            "id_document_url": ["Upload NIN/International Passport ", "Upload ID Card"],
            "passport_photo_url": ["Upload a passport photograph", "Upload Passport Photo"],
            "nok_name": ["Next of kin's full name", "Next of Kin Name"],
            "nok_phone": ["Next of kin phone number", "Next of Kin Phone"],
            "nok_email": ["Next of kin's email address", "Next of Kin Email"],
            "nok_occupation": ["Next of kin's occupation", "Next of Kin Occupation"],
            "nok_relationship": ["Relationship", "Relationship with Next of Kin"],
            "nok_address": ["Next of kin's home address", "Next of Kin Address"],
            "source_of_income": ["Source of Income"],
            "referral_source": ["How did you hear about us?"]
        }
        
        # Add NIN specially due to long prompt
        nin_keys = [k for k in row.keys() if "NIN" in k and "Lookup" in k]
        nin_keys.append("NIN")
        mapping_client["nin"] = nin_keys

        for db_col, csv_cols in mapping_client.items():
            val = get_val(row, csv_cols)
            if val:
                client_updates[db_col] = val

        # 3. Match Client in Database
        client_record = None
        
        if email:
            res = db.table("clients").select("*").ilike("email", email).execute()
            if res.data:
                client_record = res.data[0]
                
        if not client_record and full_name:
            res = db.table("clients").select("*").ilike("full_name", f"%{full_name}%").execute()
            if res.data:
                client_record = res.data[0]

        if not client_record:
            print(f"Client not found in DB: {full_name or email}. Skipping.")
            continue
            
        print(f"Matched Client: {client_record['full_name']} (ID: {client_record['id']})")

        # 4. Filter only MISSING fields (Intelligent Backfill)
        actual_updates = {}
        for col, val in client_updates.items():
            # If the database record has no value, or it's an empty string, we update it
            if not client_record.get(col) or str(client_record.get(col)).strip() == "":
                actual_updates[col] = val
                
        if actual_updates:
            try:
                db.table("clients").update(actual_updates).eq("id", client_record["id"]).execute()
                print(f"-> Updated {len(actual_updates)} missing client fields: {list(actual_updates.keys())}")
                clients_updated += 1
            except Exception as e:
                print(f"-> Failed to update client: {e}")
        else:
            print("-> No missing client fields to update.")


        # 5. Extract Potential Missing Invoice Data (Co-owner, Signature, etc.)
        property_name = get_val(row, ["Property name"])
        if not property_name:
            continue
            
        invoice_updates = {}
        mapping_invoice = {
            "co_owner_name": ['"Full name of the Second Owner\n(Surname, First name, Other Name)"', 'Full name of the Second Owner\n(Surname, First name, Other Name)', "Full name of the Second Owner"],
            "co_owner_email": ["Email address (Co-owner)"],
            "signature_url": ["Upload Signature"],
            "payment_proof_url": ["Upload receipt of payment/deposit", "Upload Payment Proof"],
            "sales_rep_name": ["Sales Rep / Marketer Name  ", "Name of Sales Rep"]
        }
        
        for db_col, csv_cols in mapping_invoice.items():
            val = get_val(row, csv_cols)
            if val:
                invoice_updates[db_col] = val

        if not invoice_updates:
            continue

        # 6. Match Invoice
        # Since property names in forms (e.g., "Prime Circle Estate Phase 1") might not perfectly 
        # match the DB ("Prime Circle Estate"), we'll first fetch all invoices for this client.
        inv_res = db.table("invoices").select("*").eq("client_id", client_record["id"]).execute()
        
        invoice_record = None
        if not inv_res.data:
            print(f"-> No invoice found for this client in the database. Constructing one from CSV data...")
            
            import re
            from datetime import date
            from utils import calculate_due_date
            
            def parse_numeric(val_str):
                cleaned = re.sub(r'[^\d.]+', '', val_str)
                if cleaned:
                    try: return float(cleaned)
                    except: pass
                return 0.0

            dep_amt = parse_numeric(get_val(row, ["Deposit Made (In Naira)"]))
            tot_amt = parse_numeric(get_val(row, ["Total Selling Price", "Property Price"]))
            plot_size_val = get_val(row, ["Plot size"])
            plot_size = parse_numeric(plot_size_val) if plot_size_val else None
            pay_duration = get_val(row, ["Payment Duration"]) or "Outright"
            pay_date = get_val(row, ["Date of Payment/Deposit ", "Payment Date"])
            inv_date = date.today()

            # Generate invoice number
            seq_result = db.rpc("generate_invoice_number").execute()
            inv_number = seq_result.data
            
            # Lookup property details
            prop_id = None
            prop_loc = None
            query = db.table("properties").select("id, total_price, price_per_sqm, location").ilike("name", f"%{property_name}%").eq("is_active", True)
            if plot_size:
                query = query.eq("plot_size_sqm", plot_size)
            prop_res = query.execute()
            
            if prop_res.data:
                p = prop_res.data[0]
                prop_id = p.get("id")
                prop_loc = p.get("location")
                if tot_amt <= 0:
                    tot_p = p.get("total_price")
                    p_sqm = p.get("price_per_sqm")
                    if tot_p and float(tot_p) > 0:
                        tot_amt = float(tot_p)
                    elif p_sqm and plot_size:
                        tot_amt = float(p_sqm) * plot_size

            due_date_str = calculate_due_date(pay_date or str(inv_date), pay_duration)

            new_inv_data = {
                "invoice_number": inv_number,
                "client_id": client_record["id"],
                "property_id": prop_id,
                "property_name": property_name,
                "property_location": prop_loc,
                "plot_size_sqm": plot_size,
                "amount": tot_amt,
                "amount_paid": dep_amt,
                "payment_terms": pay_duration,
                "invoice_date": pay_date or str(inv_date),
                "due_date": due_date_str,
                "sales_rep_name": invoice_updates.get("sales_rep_name"),
                "co_owner_name": invoice_updates.get("co_owner_name"),
                "co_owner_email": invoice_updates.get("co_owner_email"),
                "signature_url": invoice_updates.get("signature_url"),
                "payment_proof_url": invoice_updates.get("payment_proof_url"),
                "source": "google_form"
            }
            
            try:
                new_inv_res = db.table("invoices").insert(new_inv_data).execute()
                print(f"-> Created Missing Invoice {inv_number} successfully.")
                invoices_updated += 1
                
                # Also create the payment if there's a deposit
                if dep_amt > 0:
                    pay_data = {
                        "invoice_id": new_inv_res.data[0]["id"],
                        "client_id": client_record["id"],
                        "reference": f"{pay_date or str(inv_date)}_form_deposit",
                        "amount": dep_amt,
                        "payment_method": "Bank Transfer",
                        "payment_date": pay_date or str(inv_date),
                        "notes": "Initial deposit via subscription form (Backfilled)"
                    }
                    db.table("payments").insert(pay_data).execute()
                    print(f"-> Created linked deposit payment for {dep_amt}.")
                    
            except Exception as e:
                print(f"-> Failed to create invoice: {e}")
            continue
            
        if len(inv_res.data) == 1:
            # If they only have one invoice, that's almost certainly the one we want to update
            invoice_record = inv_res.data[0]
        else:
            # If multiple, try to find a substring match
            for inv in inv_res.data:
                db_prop = (inv.get("property_name") or "").lower()
                csv_prop = property_name.lower()
                if db_prop in csv_prop or csv_prop in db_prop:
                    invoice_record = inv
                    break
                    
            # Fallback to the most recent invoice if we still couldn't match
            if not invoice_record:
                sorted_invs = sorted(inv_res.data, key=lambda x: x.get("created_at", ""), reverse=True)
                invoice_record = sorted_invs[0]
        
        inv_actual_updates = {}
        for col, val in invoice_updates.items():
            if not invoice_record.get(col) or str(invoice_record.get(col)).strip() == "":
                inv_actual_updates[col] = val
                
        # Handle Sales Rep specifically - if it's missing the name but has it in form
        if "sales_rep_name" in invoice_updates and not invoice_record.get("sales_rep_name"):
            inv_actual_updates["sales_rep_name"] = invoice_updates["sales_rep_name"]

        if inv_actual_updates:
            try:
                db.table("invoices").update(inv_actual_updates).eq("id", invoice_record["id"]).execute()
                print(f"-> Updated {len(inv_actual_updates)} missing invoice fields: {list(inv_actual_updates.keys())}")
                invoices_updated += 1
            except Exception as e:
                print(f"-> Failed to update invoice: {e}")
        else:
            print("-> No missing invoice fields to update.")

    print("\n--- BACKFILL COMPLETE ---")
    print(f"Clients Updated: {clients_updated}")
    print(f"Invoices Updated: {invoices_updated}")

if __name__ == "__main__":
    main()

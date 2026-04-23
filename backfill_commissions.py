import os
import sys
from datetime import date
from database import supabase
from commission_service import get_commission_config

def backfill():
    print("Starting Commission Backfill...")
    
    # 1. Get all confirmed verifications
    verifications = supabase.table("pending_verifications")\
        .select("*, clients(*), invoices(*)")\
        .eq("status", "confirmed")\
        .execute().data
        
    print(f"Found {len(verifications)} confirmed verifications.")
    
    backfilled_count = 0
    skipped_count = 0
    
    for v in verifications:
        invoice = v["invoices"]
        client = v["clients"]
        
        if not invoice or not invoice.get("sales_rep_name"):
            print(f"Skipping V-ID {v['id']}: No Sales Rep name on invoice.")
            skipped_count += 1
            continue
            
        # Check if already has an earning
        exists = supabase.table("commission_earnings").select("id").eq("invoice_id", invoice["id"]).execute().data
        if exists:
            # print(f"Skipping V-ID {v['id']}: Earning already exists.")
            skipped_count += 1
            continue
            
        # Find Sales Rep (fuzzy)
        rep_name = invoice["sales_rep_name"].strip()
        rep_res = supabase.table("sales_reps").select("*").ilike("name", f"%{rep_name}%").execute().data
        
        if not rep_res:
            print(f"⚠️ Warning: V-ID {v['id']} - No matching rep for '{rep_name}'")
            skipped_count += 1
            continue
            
        rep = rep_res[0]
        
        # Determine rate configuration
        config = get_commission_config(
            sales_rep_id=rep["id"],
            estate_name=invoice["property_name"],
            verification_date=date.fromisoformat(v["created_at"].split("T")[0]), # Use creation date for rate check
            db=supabase
        )
        
        deposit = float(v["deposit_amount"])
        gross_comm = round(deposit * config["gross_rate"] / 100, 2)
        wht_amt = round(gross_comm * config["wht_rate"] / 100, 2)
        net_comm = gross_comm - wht_amt
        
        # Find payment record
        # Webhook creates it with '{date}_form_deposit'
        ref_expected = f"{v['payment_date']}_form_deposit"
        pay_res = supabase.table("payments").select("id").eq("invoice_id", invoice["id"]).eq("reference", ref_expected).execute().data
        if not pay_res:
            # Try fallback
            pay_res = supabase.table("payments").select("id").eq("invoice_id", invoice["id"]).ilike("reference", "%form_deposit").execute().data
            
        payment_id = pay_res[0]["id"] if pay_res else None
        
        if not payment_id:
            print(f"⚠️ Warning: V-ID {v['id']} - Could not link to a payment record.")
            skipped_count += 1
            continue
            
        # Insert
        try:
            supabase.table("commission_earnings").insert({
                "sales_rep_id": rep["id"],
                "invoice_id": invoice["id"],
                "payment_id": payment_id,
                "client_id": client["id"],
                "estate_name": invoice["property_name"],
                "payment_amount": deposit,
                "commission_rate": config["gross_rate"],
                "commission_amount": net_comm,
                "gross_commission": gross_comm,
                "wht_amount": wht_amt,
                "net_commission": net_comm,
                "created_at": v["created_at"] # Keep historical timestamp
            }).execute()
            print(f"✅ Backfilled: {rep_name} - {invoice['invoice_number']} ({fmt_currency(net_comm)})")
            backfilled_count += 1
        except Exception as e:
            print(f"❌ Error backfilling V-ID {v['id']}: {e}")
            skipped_count += 1

    print(f"\nSummary:")
    print(f"Backfilled: {backfilled_count}")
    print(f"Skipped: {skipped_count}")

def fmt_currency(val):
    return f"NGN {val:,.2f}"

if __name__ == "__main__":
    backfill()

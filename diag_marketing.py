import database
db = database.get_db()

print("--- EMAIL CAMPAIGNS ---")
camps = db.table("email_campaigns").select("*").execute()
for c in camps.data:
    print(f"  Name: {c['name']}, Status: {c['status']}, Spend: {c.get('actual_spend')}, Budget: {c.get('budget')}")

print("\n--- INVOICE COLUMNS ---")
all_invs = db.table("invoices").select("*").limit(1).execute()
if all_invs.data:
    cols = list(all_invs.data[0].keys())
    for col in sorted(cols):
        print(f"  {col}")
else:
    print("  No invoices found")

print("\n--- MARKETING CONTACTS COLUMNS ---")
conts = db.table("marketing_contacts").select("*").limit(1).execute()
if conts.data:
    for col in sorted(conts.data[0].keys()):
        print(f"  {col}")


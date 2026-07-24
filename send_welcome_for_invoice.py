import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

from database import get_db, db_execute
from email_service import send_welcome_email


async def main(invoice_number: str):
    db = get_db()

    # Try to fetch the invoice and its client
    inv_res = await db_execute(lambda: db.table("invoices").select("*, clients(*)").eq("invoice_number", invoice_number).limit(1).execute())
    if not inv_res.data:
        print(f"Invoice not found: {invoice_number}")
        return 1

    invoice = inv_res.data[0]

    # Resolve client record
    client = None
    client_raw = invoice.get("clients")
    if client_raw:
        client = client_raw[0] if isinstance(client_raw, list) and client_raw else client_raw

    if not client:
        client_res = await db_execute(lambda: db.table("clients").select("*").eq("id", invoice.get("client_id")).limit(1).execute())
        if client_res.data:
            client = client_res.data[0]

    if not client:
        print(f"Client record not found for invoice {invoice_number}")
        return 1

    prop_name = invoice.get("property_name") or ""
    print(f"Sending welcome email to {client.get('email')} for invoice {invoice_number}...")
    res = await send_welcome_email(client, prop_name)
    print("Done.")
    print("Result:", res)
    return 0


if __name__ == "__main__":
    invoice_number = sys.argv[1] if len(sys.argv) > 1 else "EC-000084"
    exit_code = asyncio.run(main(invoice_number))
    raise SystemExit(exit_code)

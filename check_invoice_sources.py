import os
from database import get_db
from dotenv import load_dotenv

load_dotenv()

def check_invoices():
    db = get_db()
    res = db.table("invoices").select("source").execute()
    sources = [row.get("source") for row in res.data]
    from collections import Counter
    counts = Counter(sources)
    print("Invoice source value counts:")
    for source, count in counts.items():
        print(f"  {source!r}: {count}")

if __name__ == "__main__":
    check_invoices()

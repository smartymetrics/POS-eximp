"""
READ-ONLY audit: scans your database for URL columns that still contain
frozen Supabase storage links (uploaded/saved before the Cloudinary
migration). Makes zero writes, zero deletes, zero updates — safe to run
any time.

Usage:
    python audit_supabase_urls.py

Output: a per-table/column count of how many rows still reference
Supabase storage directly, plus a sample of up to 3 row ids per column
so you can spot-check them.
"""
import logging
from database import get_db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

db = get_db()

# (table, url_column, id_column) — every place in the codebase that
# persists a Supabase/Cloudinary file URL into a database column.
TARGETS = [
    ("invoices", "signature_url", "id"),
    ("invoices", "contract_signature_url", "id"),
    ("invoices", "client_signature_url", "id"),
    ("invoices", "custom_lawyer_seal_url", "id"),
    ("invoices", "payment_proof_url", "id"),
    ("clients", "id_document_url", "id"),
    ("clients", "passport_photo_url", "id"),
    ("chat_messages", "file_url", "id"),
    ("staff_documents", "file_url", "id"),
    ("media_library", "file_url", "id"),
    ("expenditure_requests", "receipt_url", "id"),
    ("leave_requests", "proof_url", "id"),
    ("pending_verifications", "payment_proof_url", "id"),
    ("payments", "payment_proof_url", "id"),
    ("biodata_submissions", "passport_photo_url", "id"),
    ("biodata_submissions", "signature_url", "id"),
]

SUPABASE_MARKER = "supabase.co/storage"


def audit_column(table: str, column: str, id_column: str):
    try:
        res = (
            db.table(table)
            .select(f"{id_column},{column}")
            .ilike(column, f"%{SUPABASE_MARKER}%")
            .execute()
        )
    except Exception as e:
        return None, f"query failed: {e}"

    rows = res.data or []
    return rows, None


if __name__ == "__main__":
    logger.info("Scanning for database columns still holding Supabase storage URLs...\n")
    logger.info(f"{'Table':<25} {'Column':<25} {'Stale rows':>10}")
    logger.info("-" * 62)

    total_stale = 0
    results = []

    for table, column, id_column in TARGETS:
        rows, err = audit_column(table, column, id_column)
        if err:
            logger.info(f"{table:<25} {column:<25} {'skip: ' + err}")
            continue
        count = len(rows)
        total_stale += count
        results.append((table, column, rows))
        logger.info(f"{table:<25} {column:<25} {count:>10}")

    logger.info("-" * 62)
    logger.info(f"{'TOTAL':<51} {total_stale:>10}\n")

    if total_stale:
        logger.info("Sample rows (up to 3 per column):")
        for table, column, rows in results:
            if not rows:
                continue
            logger.info(f"\n  {table}.{column}:")
            for r in rows[:3]:
                logger.info(f"    id={r.get('id')}  {column}={r.get(column)}")
    else:
        logger.info("Nothing stale found across the tables checked — DB is clean.")

    logger.info(
        "\nThis was READ-ONLY. Nothing in your database was changed by running this script."
    )
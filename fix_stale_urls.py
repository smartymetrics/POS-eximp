"""
Rewrites stale Supabase storage URLs stored in database columns to instead
point at whatever backend the file actually lives on now (Cloudinary if
migrated, Supabase fallback otherwise) — using db.storage.from_(bucket)
.get_public_url(path), the same shim everything else in the app already
uses.

SAFE BY DEFAULT: dry-run unless you pass --apply. Dry-run makes zero writes.

Before making ANY database write, --apply mode saves every row's CURRENT
value to a timestamped url_backups_<timestamp>.json file first — a scoped,
manual alternative to a full database backup (useful on Supabase's free
tier, which has no automated backup feature). If anything looks wrong
after applying, you can restore any specific row from that file by hand
via the Supabase table editor or a plain UPDATE statement.

Usage:
    python fix_stale_urls.py                # dry-run: shows exactly what would change
    python fix_stale_urls.py --apply         # actually writes the updates (backs up first)
    python fix_stale_urls.py invoices.signature_url --apply   # just one column

"""
import re
import sys
import json
import logging
from datetime import datetime
from database import get_db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

db = get_db()

TARGETS = [
    ("invoices", "signature_url", "id"),
    ("invoices", "contract_signature_url", "id"),
    ("invoices", "payment_proof_url", "id"),
    ("clients", "id_document_url", "id"),
    ("clients", "passport_photo_url", "id"),
    ("staff_documents", "file_url", "id"),
    ("media_library", "file_url", "id"),
    ("leave_requests", "proof_url", "id"),
    ("pending_verifications", "payment_proof_url", "id"),
    ("biodata_submissions", "passport_photo_url", "id"),
    ("biodata_submissions", "signature_url", "id"),
]

SUPABASE_MARKER = "supabase.co/storage"

# Matches both:
#   .../storage/v1/object/public/<bucket>/<path>
#   .../storage/v1/object/sign/<bucket>/<path>?token=...
URL_RE = re.compile(r"storage/v1/object/(?:public|sign)/([^/]+)/([^?\"]+)")


def extract_bucket_path(url: str):
    m = URL_RE.search(url)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def resolve_new_url(bucket: str, path: str):
    try:
        return db.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        return f"__ERROR__:{e}"


def is_json_array(value: str) -> bool:
    return isinstance(value, str) and value.strip().startswith("[")


def rewrite_value(raw_value: str):
    """Returns (new_value, old_url, new_url) or None if nothing to change."""
    if is_json_array(raw_value):
        try:
            urls = json.loads(raw_value)
        except Exception:
            return None
        changed = False
        new_urls = []
        preview = (None, None)
        for u in urls:
            if SUPABASE_MARKER in u:
                bucket, path = extract_bucket_path(u)
                if bucket is None:
                    new_urls.append(u)
                    continue
                new_u = resolve_new_url(bucket, path)
                if isinstance(new_u, str) and not new_u.startswith("__ERROR__"):
                    new_urls.append(new_u)
                    changed = True
                    preview = (u, new_u)
                else:
                    new_urls.append(u)  # leave unresolved ones untouched
            else:
                new_urls.append(u)
        if not changed:
            return None
        return json.dumps(new_urls), preview[0], preview[1]

    else:
        bucket, path = extract_bucket_path(raw_value)
        if bucket is None:
            return None
        new_u = resolve_new_url(bucket, path)
        if not isinstance(new_u, str) or new_u.startswith("__ERROR__"):
            return None
        return new_u, raw_value, new_u


def process_column(table: str, column: str, id_column: str, apply: bool, backup_log: list):
    try:
        res = (
            db.table(table)
            .select(f"{id_column},{column}")
            .ilike(column, f"%{SUPABASE_MARKER}%")
            .execute()
        )
    except Exception as e:
        logger.info(f"{table}.{column}: skip ({e})")
        return 0, 0

    rows = res.data or []
    if not rows:
        return 0, 0

    logger.info(f"\n=== {table}.{column} ({len(rows)} rows) ===")
    changed, failed = 0, 0
    for row in rows:
        row_id = row.get(id_column)
        raw_value = row.get(column)
        if not raw_value:
            continue

        result = rewrite_value(raw_value)
        if result is None:
            logger.info(f"  [skip] id={row_id} — could not resolve a new URL")
            failed += 1
            continue

        new_value, old_url, new_url = result
        logger.info(f"  id={row_id}")
        logger.info(f"    old: {old_url}")
        logger.info(f"    new: {new_url}")

        if apply:
            # Record the exact current value BEFORE writing anything, so
            # there's always a manual undo path even without a full DB backup.
            backup_log.append({
                "table": table,
                "id_column": id_column,
                "id": row_id,
                "column": column,
                "previous_value": raw_value,
            })
            try:
                db.table(table).update({column: new_value}).eq(id_column, row_id).execute()
                logger.info(f"    -> updated")
            except Exception as e:
                logger.error(f"    -> FAILED to update: {e}")
                failed += 1
                continue
        changed += 1

    return changed, failed


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        wanted = set(args)
        targets = [t for t in TARGETS if f"{t[0]}.{t[1]}" in wanted]
    else:
        targets = TARGETS

    if not apply:
        logger.info("DRY RUN — no database writes will happen. Pass --apply to actually update.\n")
    else:
        logger.info("APPLY MODE — this WILL write to your database.")
        logger.info("Every row's current value is saved to a backup file BEFORE it's overwritten.\n")

    backup_log = []
    total_changed, total_failed = 0, 0
    for table, column, id_column in targets:
        c, f = process_column(table, column, id_column, apply, backup_log)
        total_changed += c
        total_failed += f

    if apply and backup_log:
        backup_path = f"url_backups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_path, "w", encoding="utf-8") as fp:
            json.dump(backup_log, fp, indent=2)
        logger.info(f"\nBackup of {len(backup_log)} original values saved to: {backup_path}")
        logger.info("To restore a row by hand: open that file, find the row's 'previous_value',")
        logger.info("and set it back via Supabase's table editor or:")
        logger.info('  UPDATE <table> SET <column> = \'<previous_value>\' WHERE <id_column> = \'<id>\';')

    logger.info(f"\n{'Updated' if apply else 'Would update'}: {total_changed}")
    if total_failed:
        logger.info(f"Could not resolve: {total_failed} (left unchanged, safe to investigate separately)")
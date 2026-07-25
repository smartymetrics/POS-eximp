"""
One-off backfill: copies every existing file out of Supabase Storage buckets
and into Cloudinary, using the same bucket/path as the Cloudinary public_id
(matches what hybrid_storage.py looks up at read time).

This does NOT delete anything from Supabase — the hybrid shim falls back to
Supabase automatically for anything not yet migrated, so it's safe to run
this incrementally, re-run it, or stop halfway.

Usage:
    python migrate_to_cloudinary.py                # migrate every known bucket
    python migrate_to_cloudinary.py signatures      # migrate just one bucket
    python migrate_to_cloudinary.py --dry-run       # list what would move, upload nothing
    python migrate_to_cloudinary.py --force         # re-upload even if already on Cloudinary
                                                     # (use once if you migrated before the
                                                     # asset_folder fix — overwrite=True in
                                                     # upload_bytes means this just replaces
                                                     # the existing asset at the same public_id,
                                                     # no duplicates get created)
"""
import sys
import logging
from database import supabase  # note: supabase.storage is ALREADY the hybrid shim
import cloudinary_client as cc

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# The real (non-shimmed) Supabase storage client, for listing + downloading
# what's currently there. supabase.storage was swapped for HybridStorage in
# database.py, so we reach through it to the original client it wraps.
_real_storage = supabase.storage._real_storage

BUCKETS = [
    "Cloud Infrastructure",   # PORTAL_CLAIMS_BUCKET (storage_service.py)
    "signatures",
    "hr-documents",           # HR_BIODATA_BUCKET
    "refund_receipts",        # REFUND_BUCKET
    "legal-vault",            # LEGAL_VAULT_BUCKET
    "marketing",
    "chat-media",
]


def list_all_files(bucket: str, prefix: str = ""):
    """Recursively list every file in a Supabase bucket (list() is one
    directory level at a time, so we walk it)."""
    files = []
    entries = _real_storage.from_(bucket).list(prefix)
    for entry in entries:
        name = entry.get("name")
        if name is None:
            continue
        full_path = f"{prefix}/{name}".lstrip("/") if prefix else name
        # Supabase folders show up as entries with id=None and no metadata
        if entry.get("id") is None and entry.get("metadata") is None:
            files.extend(list_all_files(bucket, full_path))
        else:
            files.append(full_path)
    return files


def migrate_bucket(bucket: str, dry_run: bool = False, force: bool = False):
    logger.info(f"\n=== {bucket} ===")
    try:
        paths = list_all_files(bucket)
    except Exception as e:
        logger.error(f"Could not list bucket '{bucket}': {e}")
        return 0, 0, []

    moved, skipped = 0, 0
    failures = []
    for path in paths:
        if path.endswith(".emptyFolderPlaceholder"):
            continue

        if not force and cc.resource_exists(bucket, path):
            skipped += 1
            continue

        if dry_run:
            logger.info(f"[dry-run] would migrate {bucket}/{path}")
            moved += 1
            continue

        try:
            file_bytes = _real_storage.from_(bucket).download(path)
            cc.upload_bytes(bucket, path, file_bytes)
            logger.info(f"✅ migrated {bucket}/{path}")
            moved += 1
        except Exception as e:
            logger.error(f"❌ failed {bucket}/{path}: {e}")
            failures.append((f"{bucket}/{path}", str(e)))

    logger.info(f"{bucket}: {moved} migrated, {skipped} already on Cloudinary, {len(failures)} failed")
    return moved, skipped, failures


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    targets = args if args else BUCKETS

    total_moved = 0
    all_failures = []
    for bucket in targets:
        moved, _, failures = migrate_bucket(bucket, dry_run=dry_run, force=force)
        total_moved += moved
        all_failures.extend(failures)

    logger.info(f"\nDone. {total_moved} files migrated{' (dry run, nothing uploaded)' if dry_run else ''}.")

    if all_failures:
        logger.info(f"\n=== {len(all_failures)} FAILED — still on Supabase only ===")
        for path, err in all_failures:
            logger.info(f"  {path}\n    -> {err}")

        with open("migration_failures.txt", "w", encoding="utf-8") as f:
            for path, err in all_failures:
                f.write(f"{path}\t{err}\n")
        logger.info(f"\nSaved to migration_failures.txt — re-run against a single bucket after fixing (e.g. python migrate_to_cloudinary.py legal-vault --force)")
    else:
        logger.info("No failures.")
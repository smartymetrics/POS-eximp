"""
Drop-in replacement for `supabase_client.storage`.

Every call site in the codebase does `db.storage.from_(bucket).upload(...)`
or `.create_signed_url(...)` etc. This shim exposes the exact same surface,
so no call site needs to change. Internally:

  - uploads/removes go to Cloudinary
  - reads (download / create_signed_url / get_public_url) try Cloudinary
    first, and fall back to the real Supabase storage client for files
    that haven't been migrated yet (see migrate_to_cloudinary.py)

Wired in from database.py:
    supabase.storage = HybridStorage(real_storage=supabase.storage)
"""
import logging
import requests

import cloudinary_client as cc

logger = logging.getLogger(__name__)


class _HybridBucket:
    def __init__(self, bucket: str, legacy_bucket):
        self.bucket = bucket
        self._legacy = legacy_bucket  # original supabase StorageFileAPI for this bucket

    # ---- writes -----------------------------------------------------

    def upload(self, path: str = None, file: bytes = None, file_options: dict = None, *args, **kwargs):
        # Support both positional (path, file, options) and keyword calling
        # styles — both appear across the codebase.
        if path is None and args:
            path = args[0]
        if file is None and len(args) > 1:
            file = args[1]
        if file_options is None and len(args) > 2:
            file_options = args[2]
        file_options = file_options or {}

        content_type = file_options.get("content-type") or file_options.get("content_type")

        if not file:
            logger.warning(f"⚠️  Hybrid storage: upload skipped — empty file for {self.bucket}/{path}")
            return {"path": path}

        try:
            cc.upload_bytes(self.bucket, path, file, content_type)
            logger.info(f"[Cloudinary] Uploaded {self.bucket}/{path} ({len(file) if file else 0} bytes)")
            return {"path": path}
        except Exception as e:
            logger.warning(
                f"⚠️  Cloudinary upload FAILED for {self.bucket}/{path} "
                f"[{type(e).__name__}]: {e} — falling back to Supabase"
            )
            try:
                self._legacy.upload(path=path, file=file, file_options=file_options)
                logger.info(f"↩️  Uploaded {self.bucket}/{path} to Supabase (Cloudinary fallback)")
                return {"path": path}
            except Exception as legacy_e:
                logger.error(f"❌ Upload failed on both Cloudinary and Supabase for {self.bucket}/{path}: {legacy_e}")
                raise

    def remove(self, paths: list):
        for path in paths:
            cc.delete(self.bucket, path)
        # Best-effort: also try the legacy bucket in case the file was
        # never migrated off Supabase yet. Ignore failures either way.
        try:
            self._legacy.remove(paths)
        except Exception:
            pass

    # ---- reads --------------------------------------------------------

    def download(self, path: str) -> bytes:
        resource = cc.resource_exists(self.bucket, path)
        if resource:
            url = cc.build_url(self.bucket, path, resource)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.content
        logger.info(f"↩️  Hybrid storage: {self.bucket}/{path} not on Cloudinary, falling back to Supabase")
        return self._legacy.download(path)

    def create_signed_url(self, path: str = None, expires_in: int = 3600, *args, **kwargs):
        if path is None and args:
            path = args[0]
        if args and len(args) > 1:
            expires_in = args[1]
        expires_in = kwargs.get("expires_in", expires_in)

        resource = cc.resource_exists(self.bucket, path)
        if resource:
            url = cc.build_url(self.bucket, path, resource, expires_in=expires_in)
            return {"signedURL": url, "signed_url": url}

        logger.info(f"↩️  Hybrid storage: {self.bucket}/{path} not on Cloudinary, falling back to Supabase")
        legacy_res = self._legacy.create_signed_url(path, expires_in)
        if isinstance(legacy_res, dict):
            for k in ("signedURL", "signed_url"):
                if k in legacy_res and isinstance(legacy_res[k], str) and " " in legacy_res[k]:
                    legacy_res[k] = legacy_res[k].replace(" ", "%20")
        elif isinstance(legacy_res, str) and " " in legacy_res:
            legacy_res = legacy_res.replace(" ", "%20")
        return legacy_res

    def get_public_url(self, path: str):
        resource = cc.resource_exists(self.bucket, path)
        if resource:
            return cc.build_url(self.bucket, path, resource)

        logger.info(f"↩️  Hybrid storage: {self.bucket}/{path} not on Cloudinary, falling back to Supabase")
        url = self._legacy.get_public_url(path)
        if url and isinstance(url, str) and " " in url:
            url = url.replace(" ", "%20")
        return url


class HybridStorage:
    """Replaces `supabase_client.storage`. `.from_(bucket)` returns a
    _HybridBucket that mimics the Supabase StorageFileAPI surface."""

    def __init__(self, real_storage):
        self._real_storage = real_storage
        self._buckets = {}

    def from_(self, bucket: str) -> _HybridBucket:
        if bucket not in self._buckets:
            self._buckets[bucket] = _HybridBucket(bucket, self._real_storage.from_(bucket))
        return self._buckets[bucket]

    def __getattr__(self, name):
        # Anything we haven't wrapped (list_buckets, create_bucket, etc.)
        # goes straight to the real Supabase storage client.
        return getattr(self._real_storage, name)
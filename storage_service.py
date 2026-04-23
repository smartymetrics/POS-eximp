from database import get_db
import logging
import mimetypes

logger = logging.getLogger(__name__)

PORTAL_CLAIMS_BUCKET = "Cloud Infrastructure"

def generate_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """
    Generates a secure, temporary signed URL for a file in a private bucket.
    This ensures sensitive documents like NIN, CAC, and Proformas are protected.
    """
    if not path or path.startswith("http"):
        return path # Already an external URL or empty
        
    try:
        db = get_db()
        # The modern Supabase Python SDK returns a dict with 'signedURL'
        res = db.storage.from_(bucket).create_signed_url(path, expires_in)
        
        # Handle different SDK version return types
        if isinstance(res, dict):
            return res.get('signedURL') or res.get('signed_url', "")
        return str(res)
    except Exception as e:
        logger.error(f"❌ Storage Error: Failed to generate signed URL for {path} in {bucket}: {e}")
        return ""


def upload_portal_file(file_path: str, file_bytes: bytes, content_type: str = None) -> bool:
    """
    Uploads a file to the 'Cloud Infrastructure' private bucket.

    Args:
        file_path:    Destination path inside the bucket  (e.g. 'portal_claims/abc123.pdf')
        file_bytes:   Raw file content as bytes
        content_type: MIME type; auto-detected from extension if omitted

    Returns:
        True on success, False on failure (error is logged but NOT re-raised so
        the caller can decide whether to abort or continue).
    """
    if not file_bytes:
        logger.warning(f"⚠️  Storage: upload skipped — empty file for {file_path}")
        return False

    if not content_type:
        content_type, _ = mimetypes.guess_type(file_path)
        content_type = content_type or "application/octet-stream"

    try:
        db = get_db()
        db.storage.from_(PORTAL_CLAIMS_BUCKET).upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        logger.info(f"✅ Storage: uploaded {file_path} ({len(file_bytes)} bytes)")
        return True
    except Exception as e:
        logger.error(f"❌ Storage: upload failed for {file_path}: {e}")
        return False

from database import get_db
import logging

logger = logging.getLogger(__name__)

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

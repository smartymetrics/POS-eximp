"""
Low-level Cloudinary wrapper.

Do not call cloudinary's SDK directly anywhere else in the codebase — go
through the functions here so upload/delete/URL behaviour stays consistent.
The bucket-compatibility shim (hybrid_storage.py) is what call sites
actually touch; this module just knows how to talk to Cloudinary.
"""
import os
import logging
import mimetypes
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils

logger = logging.getLogger(__name__)

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET):
    raise RuntimeError(
        "[ERROR] CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET "
        "must be set in your .env file"
    )

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

# Buckets that were PUBLIC in Supabase (served via get_public_url) keep
# working the same way on Cloudinary: plain "upload" delivery type.
# Everything else is treated as private and uploaded as "authenticated",
# which requires a signed URL to view — matching Supabase's signed-URL
# buckets (NIN, CAC, contracts, payroll docs, refund receipts, etc.)
PUBLIC_BUCKETS = {"marketing", "chat-media", "signatures"}


def resource_type_for(path: str, content_type: str = None) -> str:
    """
    Cloudinary splits assets into image / video / raw. Guess from the
    content-type first, fall back to the file extension. PDFs, docs,
    zips etc. must be 'raw' or upload/delivery will misbehave.
    """
    ct = (content_type or "").lower()
    if not ct:
        guessed, _ = mimetypes.guess_type(path)
        ct = guessed or ""

    if ct.startswith("image/"):
        return "image"
    if ct.startswith("video/") or ct.startswith("audio/"):
        return "video"
    return "raw"


def cloudinary_public_id(bucket: str, path: str) -> str:
    """Deterministic public_id so re-uploading the same logical file
    (upsert) and looking it up later always resolve to the same asset."""
    return f"{bucket}/{path}".strip("/")


def upload_bytes(bucket: str, path: str, file_bytes: bytes, content_type: str = None) -> dict:
    rtype = resource_type_for(path, content_type)
    public_id = cloudinary_public_id(bucket, path)
    delivery_type = "upload" if bucket in PUBLIC_BUCKETS else "authenticated"

    result = cloudinary.uploader.upload(
        file_bytes,
        public_id=public_id,
        resource_type=rtype,
        type=delivery_type,
        overwrite=True,
        invalidate=True,
        use_filename=False,
        unique_filename=False,
    )
    logger.info(f"✅ Cloudinary: uploaded {public_id} ({rtype}/{delivery_type})")
    return result


def resource_exists(bucket: str, path: str, content_type: str = None) -> dict | None:
    """Returns the Cloudinary resource dict if it exists, else None.
    Used by the hybrid shim to decide Cloudinary-vs-legacy-Supabase on reads."""
    public_id = cloudinary_public_id(bucket, path)
    delivery_type = "upload" if bucket in PUBLIC_BUCKETS else "authenticated"

    # We don't reliably know image/video/raw for a bare path on read, so
    # try the guessed type first, then the other two as a fallback.
    guessed = resource_type_for(path, content_type)
    for rtype in [guessed] + [t for t in ("image", "raw", "video") if t != guessed]:
        try:
            return cloudinary.api.resource(public_id, resource_type=rtype, type=delivery_type)
        except Exception:
            continue
    return None


def build_url(bucket: str, path: str, resource: dict, expires_in: int = None) -> str:
    rtype = resource.get("resource_type", "raw")
    delivery_type = resource.get("type", "authenticated")
    public_id = resource.get("public_id") or cloudinary_public_id(bucket, path)

    if delivery_type == "authenticated":
        url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type=rtype,
            type="authenticated",
            sign_url=True,
            secure=True,
        )
        return url

    return resource.get("secure_url") or cloudinary.utils.cloudinary_url(
        public_id, resource_type=rtype, type="upload", secure=True
    )[0]


def delete(bucket: str, path: str, content_type: str = None) -> bool:
    resource = resource_exists(bucket, path, content_type)
    if not resource:
        return False
    try:
        cloudinary.uploader.destroy(
            resource["public_id"],
            resource_type=resource.get("resource_type", "raw"),
            type=resource.get("type", "authenticated"),
            invalidate=True,
        )
        return True
    except Exception as e:
        logger.error(f"❌ Cloudinary: delete failed for {bucket}/{path}: {e}")
        return False
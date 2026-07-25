"""
Low-level Cloudinary wrapper.

Do not call cloudinary's SDK directly anywhere else in the codebase — go
through the functions here so upload/delete/URL behaviour stays consistent.
The bucket-compatibility shim (hybrid_storage.py) is what call sites
actually touch; this module just knows how to talk to Cloudinary.
"""
import os
import io
import logging
import mimetypes
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

# Cloudinary free-plan per-file limit. Leave a small safety margin below the
# real 10485760-byte cap since re-encoding isn't exact.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024 - 50_000

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


def _compress_image(file_bytes: bytes, path: str) -> bytes:
    """Re-encode an oversized image, stepping quality and then dimensions
    down until it fits, or Pillow isn't available."""
    if Image is None:
        logger.warning(f"⚠️  Pillow not installed — cannot compress image {path}")
        return file_bytes

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.load()
    except Exception as e:
        logger.warning(f"⚠️  Could not open {path} as an image to compress: {e}")
        return file_bytes

    fmt = "JPEG" if img.format in (None, "JPEG", "JPG") else img.format
    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Pass 1: quality steps (only meaningful for lossy formats like JPEG)
    for quality in (85, 75, 65, 50, 40):
        buf = io.BytesIO()
        try:
            img.save(buf, format=fmt, quality=quality, optimize=True)
        except Exception:
            break
        if buf.tell() <= MAX_UPLOAD_BYTES:
            logger.info(f"🗜️  Compressed {path} to quality={quality} ({buf.tell()} bytes)")
            return buf.getvalue()

    # Pass 2: still too big (common for PNGs/lossless) — downscale dimensions
    width, height = img.size
    for scale in (0.75, 0.6, 0.5, 0.35, 0.25):
        resized = img.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.LANCZOS)
        buf = io.BytesIO()
        try:
            resized.save(buf, format=fmt, quality=70, optimize=True)
        except Exception:
            resized.save(buf, format=fmt)
        if buf.tell() <= MAX_UPLOAD_BYTES:
            logger.info(f"🗜️  Compressed {path} to {scale*100:.0f}% size ({buf.tell()} bytes)")
            return buf.getvalue()

    logger.warning(f"⚠️  Could not compress {path} under the size limit — leaving as-is")
    return file_bytes


def _compress_pdf(file_bytes: bytes, path: str) -> bytes:
    """Best-effort PDF shrink: recompresses embedded images (the usual
    reason a PDF is large — scanned documents) and strips redundant
    objects. Text-heavy PDFs with few/no images won't shrink much — that's
    an inherent limit of PDF compression, not a bug here."""
    if fitz is None:
        logger.warning(f"⚠️  PyMuPDF not installed — cannot compress PDF {path}")
        return file_bytes

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        if Image is not None and hasattr(doc[0], "replace_image"):
            for page in doc:
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    try:
                        pix = fitz.Pixmap(doc, xref)
                        if pix.n - pix.alpha >= 4:  # CMYK -> RGB first
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        img = Image.frombytes(
                            "RGB" if pix.alpha == 0 else "RGBA",
                            [pix.width, pix.height],
                            pix.samples,
                        )
                        if img.mode == "RGBA":
                            img = img.convert("RGB")
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=60, optimize=True)
                        page.replace_image(xref, stream=buf.getvalue())
                    except Exception:
                        continue  # leave this particular image untouched

        result = doc.tobytes(garbage=4, deflate=True, clean=True)
        doc.close()

        if len(result) <= MAX_UPLOAD_BYTES:
            logger.info(f"🗜️  Compressed {path} ({len(file_bytes)} -> {len(result)} bytes)")
            return result
        if len(result) < len(file_bytes):
            logger.warning(
                f"⚠️  Compressed {path} some ({len(file_bytes)} -> {len(result)} bytes) "
                f"but still over {MAX_UPLOAD_BYTES} — likely text/vector-heavy content"
            )
            return result
        logger.warning(f"⚠️  Compression didn't reduce {path} — leaving as-is")
        return file_bytes
    except Exception as e:
        logger.warning(f"⚠️  PDF compression failed for {path}: {e}")
        return file_bytes


def compress_if_needed(path: str, file_bytes: bytes, content_type: str = None) -> bytes:
    if len(file_bytes) <= MAX_UPLOAD_BYTES:
        return file_bytes

    rtype = resource_type_for(path, content_type)
    logger.info(f"📦 {path} is {len(file_bytes)} bytes, over the Cloudinary limit — attempting compression")

    if rtype == "image":
        return _compress_image(file_bytes, path)
    if path.lower().endswith(".pdf") or (content_type or "").lower() == "application/pdf":
        return _compress_pdf(file_bytes, path)

    logger.warning(f"⚠️  No compressor for this file type ({path}) — leaving as-is")
    return file_bytes


def cloudinary_public_ids(bucket: str, path: str, resource_type: str) -> list[str]:
    """
    Returns candidate public_ids to try, best-first.

    For image/video, Cloudinary auto-appends the delivery format to the
    public_id — so baking the file's own extension into public_id (the
    original behaviour here) produces a doubled extension in the URL
    (e.g. "...sig.png.png"). It still resolves correctly, just cosmetically
    odd, so this stays backward-compatible: the clean, extension-stripped
    id is tried first (used for all new uploads from now on), falling back
    to the legacy full-path form so anything migrated before this fix keeps
    resolving exactly as it already does.

    For raw (PDF/doc/zip), Cloudinary does NOT auto-append a format, so the
    extension must stay in public_id — only one candidate is returned.
    """
    full = f"{bucket}/{path}".strip("/")
    if resource_type in ("image", "video"):
        root, ext = os.path.splitext(path)
        if ext:
            stripped = f"{bucket}/{root}".strip("/")
            return [stripped, full]
    return [full]


def upload_bytes(bucket: str, path: str, file_bytes: bytes, content_type: str = None) -> dict:
    file_bytes = compress_if_needed(path, file_bytes, content_type)

    rtype = resource_type_for(path, content_type)
    public_id = cloudinary_public_ids(bucket, path, rtype)[0]
    delivery_type = "upload" if bucket in PUBLIC_BUCKETS else "authenticated"

    # Dynamic Folder mode (default on all accounts created since June 2024)
    # decouples the public_id path from Media Library folders — slashes in
    # public_id alone no longer create visible folders. asset_folder is what
    # actually organizes the Media Library UI; it doesn't affect the
    # public_id or delivery URL, so our lookup logic is unaffected.
    asset_folder = "/".join(public_id.split("/")[:-1]) or bucket

    result = cloudinary.uploader.upload(
        file_bytes,
        public_id=public_id,
        asset_folder=asset_folder,
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
    delivery_type = "upload" if bucket in PUBLIC_BUCKETS else "authenticated"

    # We don't reliably know image/video/raw for a bare path on read, so
    # try the guessed type first, then the other two as a fallback. For
    # each type, try the clean (post-fix) public_id before the legacy
    # extension-doubled one.
    guessed = resource_type_for(path, content_type)
    for rtype in [guessed] + [t for t in ("image", "raw", "video") if t != guessed]:
        for public_id in cloudinary_public_ids(bucket, path, rtype):
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
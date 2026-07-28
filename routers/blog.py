"""
Blog module — write, review/approval workflow, curation placements, media,
comments, reactions, share-preview links, and audit logging.

Follows existing project conventions:
- Supabase via get_db() / db_execute()
- Auth via routers.auth.verify_token / has_any_role / resolve_admin_token
- Notifications via routers.notifications.create_notification
- Roles are plain comma-separated strings on admins.role — this module adds
  three new role strings that admins can be assigned in User Management:
    blog_publisher   -> approve/reject/publish/edit any post, manage own drafts
    blog_curator     -> manage homepage placements (featured/ticker/top content)
    blog_moderator   -> hide/delete public comments
  "admin" / "super_admin" always pass every check (has_any_role handles this).
"""

import os
import re
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, EmailStr

from database import get_db, db_execute
from routers.auth import verify_token, has_any_role
from routers.notifications import create_notification

BLOG_MEDIA_BUCKET = "blog-media"

logger = logging.getLogger(__name__)
router = APIRouter()

PUBLISHER_ROLES = ["admin", "super_admin", "blog_publisher"]
CURATOR_ROLES = ["admin", "super_admin", "blog_curator"]
MODERATOR_ROLES = ["admin", "super_admin", "blog_moderator", "blog_publisher", "blog_curator"]


# ─────────────────────────── helpers ───────────────────────────

def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or str(uuid.uuid4())[:8]


async def log_action(post_id: str, actor_id: Optional[str], action: str, comment: str = None):
    db = get_db()
    await db_execute(lambda: db.table("blog_audit_log").insert({
        "post_id": post_id,
        "actor_id": actor_id,
        "action": action,
        "comment": comment,
    }).execute())


async def notify_publishers(title: str, message: str, ref_id: str, n_type: str = "blog_review"):
    db = get_db()
    admins_res = await db_execute(lambda: db.table("admins").select("id, role").execute())
    target_ids = []
    for adm in (admins_res.data or []):
        roles = [r.strip().lower() for r in (adm.get("role") or "").split(",") if r.strip()]
        if any(r in {"admin", "super_admin", "blog_publisher"} for r in roles):
            target_ids.append(adm["id"])
    for admin_id in target_ids:
        await create_notification(admin_id, title, message, n_type=n_type, ref_id=ref_id)


async def get_post_or_404(post_id: str) -> dict:
    db = get_db()
    res = await db_execute(lambda: db.table("blog_posts").select("*").eq("id", post_id).execute())
    if not res.data:
        raise HTTPException(404, "Post not found")
    return res.data[0]


async def _enrich_author_data(posts_list: List[dict]) -> List[dict]:
    """Ensures author_name_snapshot and author_department_snapshot are present.
    Preserves the static historical snapshot stored on the post (capturing the
    writer's department at creation/publication from HR data). Only queries the
    admins table as a fallback if snapshot fields are missing or empty."""
    if not posts_list:
        return posts_list

    missing_author_ids = list({
        p["author_id"] for p in posts_list
        if isinstance(p, dict) and p.get("author_id") and (not p.get("author_name_snapshot") or not p.get("author_department_snapshot"))
    })

    admin_map = {}
    if missing_author_ids:
        db = get_db()
        try:
            admins_res = await db_execute(
                lambda: db.table("admins").select("id, full_name, department").in_("id", missing_author_ids).execute()
            )
            admin_map = {a["id"]: a for a in (admins_res.data or [])}
        except Exception as e:
            logger.warning(f"Failed to fetch fallback admin author info: {e}")

    for post in posts_list:
        if not isinstance(post, dict):
            continue
        aid = post.get("author_id")

        # Fallback to admins table ONLY if snapshot fields are missing
        if aid and aid in admin_map:
            adm = admin_map[aid]
            if not post.get("author_name_snapshot") and adm.get("full_name"):
                post["author_name_snapshot"] = adm["full_name"]
            if not post.get("author_department_snapshot") and adm.get("department"):
                post["author_department_snapshot"] = adm["department"]

        # Default fallbacks if still empty
        if not post.get("author_name_snapshot"):
            post["author_name_snapshot"] = "Eximp & Cloves Team"
        if not post.get("author_department_snapshot"):
            post["author_department_snapshot"] = "General"

    return posts_list


# ─────────────────────────── models ───────────────────────────

class PostCreate(BaseModel):
    title: str
    content: dict = {}
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    tags: List[str] = []
    category: Optional[str] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[dict] = None
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None


class NewsletterSubscribeRequest(BaseModel):
    email: str


class ProfileCompleteRequest(BaseModel):
    token: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[str] = None
    phone: Optional[str] = None


class RejectRequest(BaseModel):
    comment: str


class MediaAttach(BaseModel):
    media_type: str  # image | video
    source: str      # upload | url | youtube
    url: str
    caption: Optional[str] = None


class PlacementCreate(BaseModel):
    placement_type: str
    post_id: str
    position: int = 0
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None


class CommentCreate(BaseModel):
    author_name: str
    author_email: EmailStr
    content: str
    parent_comment_id: Optional[str] = None


class HideCommentRequest(BaseModel):
    reason: Optional[str] = None


class ReactionRequest(BaseModel):
    reader_identifier: str
    reaction_type: str = "like"


class StaffRoleUpdate(BaseModel):
    can_publish: bool
    can_curate: bool
    can_moderate: bool = False


# ─────────────────────────── posts: create / list / detail ───────────────────────────

@router.post("/posts")
async def create_post(data: PostCreate, current_admin=Depends(verify_token)):
    db = get_db()
    admin_res = await db_execute(
        lambda: db.table("admins").select("full_name, department").eq("id", current_admin["sub"]).execute()
    )
    admin = admin_res.data[0] if admin_res.data else {}

    slug = slugify(data.title)
    # ensure uniqueness
    existing = await db_execute(lambda: db.table("blog_posts").select("id").eq("slug", slug).execute())
    if existing.data:
        slug = f"{slug}-{str(uuid.uuid4())[:6]}"

    row = {
        "title": data.title,
        "slug": slug,
        "content": data.content,
        "excerpt": data.excerpt,
        "cover_image_url": data.cover_image_url,
        "status": "draft",
        "author_id": current_admin["sub"],
        "author_name_snapshot": admin.get("full_name"),
        "author_department_snapshot": admin.get("department"),
        "seo_title": data.seo_title,
        "seo_description": data.seo_description,
        "tags": data.tags,
        "category": data.category,
    }
    res = await db_execute(lambda: db.table("blog_posts").insert(row).execute())
    post = res.data[0]
    await log_action(post["id"], current_admin["sub"], "created")
    return post


@router.get("/posts")
async def list_posts(status: Optional[str] = None, mine: bool = False, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("blog_posts").select("*").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    if mine:
        query = query.eq("author_id", current_admin["sub"])
    res = await db_execute(lambda: query.execute())
    posts = await _enrich_author_data(res.data or [])
    return posts


@router.get("/posts/{post_id}")
async def get_post(post_id: str, current_admin=Depends(verify_token)):
    post = await get_post_or_404(post_id)
    enriched = await _enrich_author_data([post])
    return enriched[0]


@router.patch("/posts/{post_id}")
async def update_post(post_id: str, data: PostUpdate, current_admin=Depends(verify_token)):
    post = await get_post_or_404(post_id)
    is_publisher = has_any_role(current_admin, PUBLISHER_ROLES)
    is_author = post["author_id"] == current_admin["sub"]

    if not (is_publisher or (is_author and post["status"] in ("draft", "rejected"))):
        raise HTTPException(403, "Not authorized to edit this post")

    db = get_db()
    updates = {k: v for k, v in data.dict(exclude_unset=True).items() if v is not None}
    if not updates:
        return post
    updates["updated_at"] = datetime.utcnow().isoformat()
    res = await db_execute(lambda: db.table("blog_posts").update(updates).eq("id", post_id).execute())
    await log_action(post_id, current_admin["sub"], "edited")
    return res.data[0]


# ─────────────────────────── review workflow ───────────────────────────

@router.post("/posts/{post_id}/submit")
async def submit_for_review(post_id: str, current_admin=Depends(verify_token)):
    """Any staff can submit their own draft. Non-publishers MUST go through
    review; publishers may also choose this instead of direct publish."""
    post = await get_post_or_404(post_id)
    if post["author_id"] != current_admin["sub"] and not has_any_role(current_admin, PUBLISHER_ROLES):
        raise HTTPException(403, "Not authorized")

    db = get_db()
    await db_execute(lambda: db.table("blog_posts").update({
        "status": "pending_review",
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", post_id).execute())
    await log_action(post_id, current_admin["sub"], "submitted")

    await notify_publishers(
        title="New blog post pending review",
        message=f"\"{post['title']}\" by {post.get('author_name_snapshot') or 'a staff member'} is awaiting review.",
        ref_id=post_id,
    )
    return {"status": "pending_review"}


@router.post("/posts/{post_id}/publish")
async def publish_post(post_id: str, current_admin=Depends(verify_token)):
    """Direct publish — publisher role required. Used both for approving a
    pending_review post and for a publisher's own draft going straight live."""
    if not has_any_role(current_admin, PUBLISHER_ROLES):
        raise HTTPException(403, "Not authorized to publish")
    post = await get_post_or_404(post_id)

    db = get_db()
    was_pending = post["status"] == "pending_review"

    # Sync author's latest name and department from HR (admins table)
    author_res = await db_execute(
        lambda: db.table("admins").select("full_name, department").eq("id", post["author_id"]).execute()
    )
    author_info = author_res.data[0] if author_res.data else {}

    update_payload = {
        "status": "published",
        "reviewed_by_id": current_admin["sub"],
        "reviewed_at": datetime.utcnow().isoformat(),
        "published_at": post.get("published_at") or datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if not post.get("author_name_snapshot") and author_info.get("full_name"):
        update_payload["author_name_snapshot"] = author_info["full_name"]
    if not post.get("author_department_snapshot") and author_info.get("department"):
        update_payload["author_department_snapshot"] = author_info["department"]

    await db_execute(lambda: db.table("blog_posts").update(update_payload).eq("id", post_id).execute())

    await log_action(post_id, current_admin["sub"], "approved" if was_pending else "published")
    return {"status": "published"}


@router.post("/posts/{post_id}/unpublish")
async def unpublish_post(post_id: str, current_admin=Depends(verify_token)):
    """Revert a published post back to draft — publisher role required."""
    if not has_any_role(current_admin, PUBLISHER_ROLES):
        raise HTTPException(403, "Not authorized to unpublish")
    post = await get_post_or_404(post_id)

    db = get_db()
    await db_execute(lambda: db.table("blog_posts").update({
        "status": "draft",
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", post_id).execute())

    # Clean up homepage placements if any
    await db_execute(lambda: db.table("blog_placements").delete().eq("post_id", post_id).execute())

    await log_action(post_id, current_admin["sub"], "unpublished")
    return {"status": "draft"}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, current_admin=Depends(verify_token)):
    """Delete a post — publisher role required or author deleting their own draft."""
    post = await get_post_or_404(post_id)
    is_publisher = has_any_role(current_admin, PUBLISHER_ROLES)
    is_author = post["author_id"] == current_admin["sub"]

    if not (is_publisher or (is_author and post["status"] in ("draft", "rejected"))):
        raise HTTPException(403, "Not authorized to delete this post")

    db = get_db()
    await db_execute(lambda: db.table("blog_placements").delete().eq("post_id", post_id).execute())
    await db_execute(lambda: db.table("blog_posts").delete().eq("id", post_id).execute())
    await log_action(post_id, current_admin["sub"], "deleted")
    return {"status": "deleted"}


@router.post("/posts/{post_id}/reject")
async def reject_post(post_id: str, data: RejectRequest, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, PUBLISHER_ROLES):
        raise HTTPException(403, "Not authorized to review")
    post = await get_post_or_404(post_id)

    db = get_db()
    await db_execute(lambda: db.table("blog_posts").update({
        "status": "rejected",
        "reviewed_by_id": current_admin["sub"],
        "reviewed_at": datetime.utcnow().isoformat(),
        "review_comment": data.comment,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", post_id).execute())
    await log_action(post_id, current_admin["sub"], "rejected", comment=data.comment)

    await create_notification(
        post["author_id"],
        "Your blog post needs changes",
        f"\"{post['title']}\" was sent back: {data.comment}",
        n_type="blog_review",
        ref_id=post_id,
    )
    return {"status": "rejected"}


@router.get("/posts/{post_id}/audit-log")
async def get_audit_log(post_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(
        lambda: db.table("blog_audit_log").select("*").eq("post_id", post_id).order("created_at").execute()
    )
    return res.data


# ─────────────────────────── share / preview links ───────────────────────────

@router.post("/posts/{post_id}/share-link")
async def create_share_link(post_id: str, current_admin=Depends(verify_token)):
    post = await get_post_or_404(post_id)
    if post["author_id"] != current_admin["sub"] and not has_any_role(current_admin, PUBLISHER_ROLES):
        raise HTTPException(403, "Not authorized")

    token = str(uuid.uuid4())
    db = get_db()
    await db_execute(lambda: db.table("blog_posts").update({"share_token": token}).eq("id", post_id).execute())
    await log_action(post_id, current_admin["sub"], "share_link_created")
    return {"share_token": token, "preview_path": f"/blog/preview/{post['slug']}?token={token}"}


@router.delete("/posts/{post_id}/share-link")
async def revoke_share_link(post_id: str, current_admin=Depends(verify_token)):
    post = await get_post_or_404(post_id)
    if post["author_id"] != current_admin["sub"] and not has_any_role(current_admin, PUBLISHER_ROLES):
        raise HTTPException(403, "Not authorized")

    db = get_db()
    await db_execute(lambda: db.table("blog_posts").update({"share_token": None}).eq("id", post_id).execute())
    await log_action(post_id, current_admin["sub"], "share_link_revoked")
    return {"status": "revoked"}


# ─────────────────────────── media ───────────────────────────

@router.post("/upload-image")
async def upload_blog_image(file: UploadFile = File(...), current_admin=Depends(verify_token)):
    """Real file upload for the GrapesJS Asset Manager. Response shape
    ({"data": [url]}) matches what GrapesJS expects (same convention used
    by /api/marketing/media/upload)."""
    db = get_db()
    contents = await file.read()
    ext = (file.filename or "upload").split(".")[-1] if file.filename and "." in file.filename else ""
    path = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
    try:
        db.storage.from_(BLOG_MEDIA_BUCKET).upload(
            path=path, file=contents, file_options={"content-type": file.content_type, "upsert": "true"}
        )
        url = db.storage.from_(BLOG_MEDIA_BUCKET).get_public_url(path)
    except Exception as e:
        logger.error(f"Blog image upload failed: {e}")
        raise HTTPException(500, "Upload failed")
    return {"data": [url]}


@router.post("/posts/{post_id}/media")
async def attach_media(post_id: str, data: MediaAttach, current_admin=Depends(verify_token)):
    await get_post_or_404(post_id)
    db = get_db()
    res = await db_execute(lambda: db.table("blog_media").insert({
        "post_id": post_id,
        "media_type": data.media_type,
        "source": data.source,
        "url": data.url,
        "caption": data.caption,
    }).execute())
    return res.data[0]


@router.delete("/media/{media_id}")
async def delete_media(media_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    await db_execute(lambda: db.table("blog_media").delete().eq("id", media_id).execute())
    return {"status": "deleted"}


# ─────────────────────────── curation placements ───────────────────────────

@router.get("/placements")
async def list_placements(placement_type: Optional[str] = None, current_admin=Depends(verify_token)):
    db = get_db()
    query = db.table("blog_placements").select("*, blog_posts(id, title, slug, cover_image_url, status)").order("position")
    if placement_type:
        query = query.eq("placement_type", placement_type)
    res = await db_execute(lambda: query.execute())
    return res.data


@router.post("/placements")
async def create_placement(data: PlacementCreate, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, CURATOR_ROLES):
        raise HTTPException(403, "Not authorized to curate")
    post = await get_post_or_404(data.post_id)
    if post["status"] != "published":
        raise HTTPException(400, "Only published posts can be placed")

    db = get_db()
    row = data.dict()
    row["created_by"] = current_admin["sub"]
    res = await db_execute(lambda: db.table("blog_placements").insert(row).execute())
    return res.data[0]


@router.delete("/placements/{placement_id}")
async def delete_placement(placement_id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, CURATOR_ROLES):
        raise HTTPException(403, "Not authorized to curate")
    db = get_db()
    await db_execute(lambda: db.table("blog_placements").delete().eq("id", placement_id).execute())
    return {"status": "deleted"}


# ─────────────────────────── comment moderation (ERP side) ───────────────────────────

@router.get("/posts/{post_id}/comments")
async def list_comments_admin(post_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    res = await db_execute(
        lambda: db.table("blog_comments").select("*").eq("post_id", post_id).order("created_at").execute()
    )
    return res.data


@router.patch("/comments/{comment_id}/hide")
async def hide_comment(comment_id: str, data: HideCommentRequest, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, MODERATOR_ROLES):
        raise HTTPException(403, "Not authorized to moderate comments")
    db = get_db()
    res = await db_execute(lambda: db.table("blog_comments").update({
        "status": "hidden",
        "hidden_by": current_admin["sub"],
        "hidden_at": datetime.utcnow().isoformat(),
        "hidden_reason": data.reason,
    }).eq("id", comment_id).execute())
    return res.data[0]


@router.patch("/comments/{comment_id}/unhide")
async def unhide_comment(comment_id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, MODERATOR_ROLES):
        raise HTTPException(403, "Not authorized to moderate comments")
    db = get_db()
    res = await db_execute(lambda: db.table("blog_comments").update({
        "status": "approved",
        "hidden_by": None,
        "hidden_at": None,
        "hidden_reason": None,
    }).eq("id", comment_id).execute())
    return res.data[0]


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, MODERATOR_ROLES):
        raise HTTPException(403, "Not authorized to moderate comments")
    db = get_db()
    await db_execute(lambda: db.table("blog_comments").update({"status": "deleted"}).eq("id", comment_id).execute())
    return {"status": "deleted"}


# ─────────────────────────── PUBLIC endpoints (no auth — used by the website) ───────────────────────────

@router.get("/public/posts")
async def public_list_posts(page: int = 1, page_size: int = 10, category: Optional[str] = None):
    db = get_db()
    start = (page - 1) * page_size
    end = start + page_size - 1
    query = db.table("blog_posts").select(
        "id, title, slug, excerpt, cover_image_url, tags, category, published_at, author_id, author_name_snapshot, author_department_snapshot",
        count="exact",
    ).eq("status", "published").order("published_at", desc=True).range(start, end)
    if category:
        query = query.eq("category", category)
    res = await db_execute(lambda: query.execute())
    posts = await _enrich_author_data(res.data or [])
    return {"posts": posts, "total": res.count, "page": page, "page_size": page_size}


@router.get("/public/posts/{slug}")
async def public_get_post(slug: str):
    db = get_db()
    res = await db_execute(
        lambda: db.table("blog_posts").select("*").eq("slug", slug).eq("status", "published").execute()
    )
    if not res.data:
        raise HTTPException(404, "Post not found")
    posts = await _enrich_author_data(res.data)
    return posts[0]


@router.get("/public/preview/{slug}")
async def public_preview_post(slug: str, token: str):
    """Token-gated preview of a draft/pending_review/rejected post. Route
    should be rendered with `noindex` at the frontend/SSR layer."""
    db = get_db()
    res = await db_execute(lambda: db.table("blog_posts").select("*").eq("slug", slug).execute())
    if not res.data or res.data[0].get("share_token") != token:
        raise HTTPException(404, "Preview not found or link revoked")
    posts = await _enrich_author_data(res.data)
    return posts[0]


@router.get("/public/placements/{placement_type}")
async def public_placements(placement_type: str):
    db = get_db()
    res = await db_execute(
        lambda: db.table("blog_placements")
        .select("position, blog_posts(id, title, slug, excerpt, cover_image_url, published_at, author_id, author_name_snapshot, author_department_snapshot)")
        .eq("placement_type", placement_type)
        .order("position")
        .execute()
    )
    active = [p for p in res.data if p.get("blog_posts")]
    if active:
        raw_posts = [p["blog_posts"] for p in active]
        enriched_posts = await _enrich_author_data(raw_posts)
        enriched_map = {p["id"]: p for p in enriched_posts}
        for item in active:
            pid = item["blog_posts"]["id"]
            if pid in enriched_map:
                item["blog_posts"] = enriched_map[pid]
    return active


@router.post("/public/posts/{post_id}/comments")
async def public_add_comment(post_id: str, data: CommentCreate, background_tasks: BackgroundTasks):
    await get_post_or_404(post_id)
    db = get_db()
    res = await db_execute(lambda: db.table("blog_comments").insert({
        "post_id": post_id,
        "parent_comment_id": data.parent_comment_id,
        "author_name": data.author_name,
        "author_email": data.author_email,
        "content": data.content,
    }).execute())
    background_tasks.add_task(_notify_new_comment_bg, post_id)
    return res.data[0]


async def _notify_new_comment_bg(post_id: str):
    post = await get_post_or_404(post_id)
    await notify_publishers(
        title="New comment awaiting moderation",
        message=f"A new comment was posted on \"{post['title']}\".",
        ref_id=post_id,
        n_type="blog_comment",
    )


@router.get("/public/posts/{post_id}/comments")
async def public_list_comments(post_id: str):
    db = get_db()
    res = await db_execute(
        lambda: db.table("blog_comments").select("id, author_name, content, parent_comment_id, created_at")
        .eq("post_id", post_id).eq("status", "visible").order("created_at").execute()
    )
    return res.data


@router.post("/public/posts/{post_id}/react")
async def public_react(post_id: str, data: ReactionRequest):
    await get_post_or_404(post_id)
    db = get_db()
    try:
        await db_execute(lambda: db.table("blog_reactions").insert({
            "post_id": post_id,
            "reader_identifier": data.reader_identifier,
            "reaction_type": data.reaction_type,
        }).execute())
    except Exception:
        pass  # unique constraint -> already reacted, treat as no-op
    count_res = await db_execute(
        lambda: db.table("blog_reactions").select("id", count="exact").eq("post_id", post_id).execute()
    )
    return {"total_reactions": count_res.count}


@router.get("/public/posts/{post_id}/reactions")
async def public_reaction_count(post_id: str):
    db = get_db()
    count_res = await db_execute(
        lambda: db.table("blog_reactions").select("id", count="exact").eq("post_id", post_id).execute()
    )
    return {"total_reactions": count_res.count}


# ─────────────────────────── staff blog permissions management ───────────────────────────

@router.get("/admin/staff-roles")
async def list_staff_roles(current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, ["admin", "super_admin"]):
        raise HTTPException(403, "Only admins can manage staff blog roles")
    db = get_db()
    res = await db_execute(
        lambda: db.table("admins").select("id, full_name, email, department, role, is_active").order("full_name").execute()
    )
    result = []
    for adm in (res.data or []):
        roles = [r.strip().lower() for r in (adm.get("role") or "").split(",") if r.strip()]
        is_admin = any(r in {"admin", "super_admin"} for r in roles)
        result.append({
            "id": adm["id"],
            "full_name": adm.get("full_name") or adm.get("email"),
            "email": adm.get("email"),
            "department": adm.get("department") or "N/A",
            "role": adm.get("role") or "",
            "is_admin": is_admin,
            "can_publish": is_admin or "blog_publisher" in roles,
            "can_curate": is_admin or "blog_curator" in roles,
            "can_moderate": is_admin or "blog_moderator" in roles,
        })
    return result


@router.patch("/admin/staff-roles/{admin_id}")
async def update_staff_blog_roles(admin_id: str, data: StaffRoleUpdate, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, ["admin", "super_admin"]):
        raise HTTPException(403, "Only admins can manage staff blog roles")
    db = get_db()
    adm_res = await db_execute(lambda: db.table("admins").select("role").eq("id", admin_id).execute())
    if not adm_res.data:
        raise HTTPException(404, "Staff member not found")

    current_roles = [r.strip().lower() for r in (adm_res.data[0].get("role") or "").split(",") if r.strip()]
    role_set = set(current_roles)

    if data.can_publish:
        role_set.add("blog_publisher")
    else:
        role_set.discard("blog_publisher")

    if data.can_curate:
        role_set.add("blog_curator")
    else:
        role_set.discard("blog_curator")

    if data.can_moderate:
        role_set.add("blog_moderator")
    else:
        role_set.discard("blog_moderator")

    new_role_str = ",".join(sorted(role_set))
    res = await db_execute(lambda: db.table("admins").update({"role": new_role_str}).eq("id", admin_id).execute())
    return {"status": "updated", "role": new_role_str}


# ─────────────────────────── public newsletter & double opt-in ───────────────────────────

async def _send_newsletter_verification_email(to_email: str, token: str):
    site_url = os.getenv("SITE_URL", "https://eximps-cloves.com")
    verify_link = f"{site_url}/verify-subscription?token={token}"
    subject = "Confirm your subscription to Eximp & Cloves Insights"
    html = f"""
    <div style="font-family:'Inter',system-ui,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
      <div style="background:#0F1115;padding:24px 32px;border-bottom:3px solid #C47D0A;">
        <span style="color:#C47D0A;font-weight:800;font-size:18px;letter-spacing:0.05em;">EXIMP &amp; CLOVES</span>
        <span style="color:#9CA3AF;font-size:12px;margin-left:8px;">INSIGHTS</span>
      </div>
      <div style="padding:32px;color:#1F2937;">
        <h2 style="color:#111827;font-size:22px;margin-top:0;">Verify Your Email Address</h2>
        <p style="font-size:15px;line-height:1.6;color:#4B5563;">
          Thank you for subscribing to Eximp &amp; Cloves Insights! Please click the button below to verify your email address and confirm your subscription.
        </p>
        <div style="margin:28px 0;text-align:center;">
          <a href="{verify_link}" style="background:#C47D0A;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:700;font-size:14px;display:inline-block;">
            Confirm Subscription
          </a>
        </div>
        <p style="font-size:13px;color:#6B7280;line-height:1.5;">
          If the button above does not work, copy and paste this link into your browser:<br>
          <a href="{verify_link}" style="color:#C47D0A;word-break:break-all;">{verify_link}</a>
        </p>
        <p style="font-size:12px;color:#9CA3AF;margin-top:24px;">
          If you did not request this subscription, you can safely ignore this email.
        </p>
      </div>
      <div style="background:#F9FAFB;padding:20px 32px;border-top:1px solid #E5E7EB;font-size:11px;color:#9CA3AF;text-align:center;">
        Eximp &amp; Cloves Infrastructure Limited · 57B Isaac John Street, Yaba, Lagos
      </div>
    </div>
    """
    try:
        import resend
        if not getattr(resend, "api_key", None):
            resend.api_key = os.getenv("RESEND_API_KEY")
        from_addr = os.getenv("FROM_EMAIL", "newsletter@eximps-cloves.com")
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: resend.Emails.send({
            "from": f"Eximp & Cloves <{from_addr}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
        }))
    except Exception as e:
        logger.error(f"Failed to send newsletter verification email to {to_email}: {e}")


@router.post("/public/newsletter/subscribe")
async def public_newsletter_subscribe(data: NewsletterSubscribeRequest, background_tasks: BackgroundTasks):
    email = (data.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Please provide a valid email address.")

    db = get_db()
    token = str(uuid.uuid4())
    expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()

    try:
        await db_execute(lambda: db.table("blog_newsletter_subscriptions").upsert({
            "email": email,
            "verification_token": token,
            "status": "pending",
            "token_expires_at": expires_at,
            "updated_at": datetime.utcnow().isoformat(),
        }, on_conflict="email").execute())
    except Exception as e:
        logger.warning(f"Newsletter subscription database upsert error: {e}")

    background_tasks.add_task(_send_newsletter_verification_email, email, token)

    return {
        "status": "pending_verification",
        "message": "Verification link sent! Please check your email to confirm your subscription."
    }


@router.get("/public/newsletter/verify")
async def public_newsletter_verify(token: str):
    if not token:
        raise HTTPException(400, "Verification token is required.")

    db = get_db()
    sub_res = await db_execute(
        lambda: db.table("blog_newsletter_subscriptions").select("*").eq("verification_token", token).execute()
    )
    if not sub_res.data:
        raise HTTPException(404, "Invalid or expired verification link.")

    sub = sub_res.data[0]
    email = sub["email"]

    # Update subscription to verified
    await db_execute(lambda: db.table("blog_newsletter_subscriptions").update({
        "status": "verified",
        "verified_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", sub["id"]).execute())

    # Check if client exists in clients table
    client_res = await db_execute(
        lambda: db.table("clients").select("id, client_type, first_name, last_name, phone").eq("email", email).execute()
    )
    is_client = bool(client_res.data)
    client_info = client_res.data[0] if is_client else {}

    # Upsert into marketing_contacts table (Lead or Client)
    contact_type = "client" if is_client else "lead"
    contact_payload = {
        "email": email,
        "contact_type": contact_type,
        "source": "newsletter_double_optin",
        "is_subscribed": True,
        "tags": ["newsletter", "double_optin_verified"],
        "engagement_score": 10,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if client_info.get("first_name"):
        contact_payload["first_name"] = client_info["first_name"]
    if client_info.get("last_name"):
        contact_payload["last_name"] = client_info["last_name"]
    if client_info.get("phone"):
        contact_payload["phone"] = client_info["phone"]

    try:
        await db_execute(
            lambda: db.table("marketing_contacts").upsert(contact_payload, on_conflict="email").execute()
        )
    except Exception as e:
        logger.warning(f"Error syncing marketing_contacts for {email}: {e}")

    return {
        "status": "verified",
        "email": email,
        "is_client": is_client,
        "message": "Subscription verified successfully! Welcome to Eximp & Cloves Insights."
    }


@router.post("/public/newsletter/complete-profile")
async def public_newsletter_complete_profile(data: ProfileCompleteRequest):
    if not data.token:
        raise HTTPException(400, "Token is required.")

    db = get_db()
    sub_res = await db_execute(
        lambda: db.table("blog_newsletter_subscriptions").select("email").eq("verification_token", data.token).execute()
    )
    if not sub_res.data:
        raise HTTPException(404, "Invalid token.")

    email = sub_res.data[0]["email"]

    updates = {"updated_at": datetime.utcnow().isoformat()}
    if data.first_name:
        updates["first_name"] = data.first_name.strip()
    if data.last_name:
        updates["last_name"] = data.last_name.strip()
    if data.dob:
        updates["dob"] = data.dob.strip()
    if data.phone:
        updates["phone"] = data.phone.strip()

    await db_execute(
        lambda: db.table("marketing_contacts").update(updates).eq("email", email).execute()
    )

    return {
        "status": "success",
        "message": "Thank you! Your profile has been updated."
    }

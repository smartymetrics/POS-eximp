"""
routers/hrm_talent_chat.py
──────────────────────────
REST + WebSocket backend for the Talent Pool Chat feature.

Endpoints
─────────
GET  /api/hr/talent-chat/rooms               – list all rooms (HR)
POST /api/hr/talent-chat/rooms               – open/get room for a candidate
GET  /api/hr/talent-chat/rooms/{id}/messages – paginated message history
POST /api/hr/talent-chat/rooms/{id}/messages – HR sends a text message
POST /api/hr/talent-chat/rooms/{id}/upload   – file upload (multipart)
PATCH /api/hr/talent-chat/rooms/{id}/read    – mark HR messages as read

Public (applicant, auth by token):
GET  /api/talent-chat/portal/{token}         – HTML portal page
GET  /api/talent-chat/{token}/messages       – applicant fetches history
POST /api/talent-chat/{token}/messages       – applicant sends text
POST /api/talent-chat/{token}/upload         – applicant uploads file
PATCH /api/talent-chat/{token}/read          – mark applicant msgs read

WebSocket (both sides):
WS   /api/ws/talent-chat/{room_id}?token=…  – real-time bi-directional

Background:
POST /api/hr/talent-chat/check-followups     – called by scheduler / cron
"""

from fastapi import (
    APIRouter, WebSocket, WebSocketDisconnect,
    Depends, HTTPException, BackgroundTasks,
    UploadFile, File, Form, Query
)
from fastapi.responses import HTMLResponse
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import asyncio
import json
import os
import uuid
import mimetypes

from database import get_db, db_execute
from routers.auth import require_roles, resolve_admin_token

router = APIRouter()

# ─── Storage helper ──────────────────────────────────────────────────────────
# Reuse Supabase Storage if configured, else fall back to local /static/uploads
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_KEY", ""))
TALENT_BUCKET = "hr_documents"
LOCAL_UPLOAD_DIR = "static/uploads/talent_chat"

os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)


async def _store_file(data: bytes, filename: str, mime: str) -> str:
    """Return a public URL for the stored file."""
    safe_name = f"{uuid.uuid4().hex}_{filename}"

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            import httpx
            async with httpx.AsyncClient() as c:
                r = await c.post(
                    f"{SUPABASE_URL}/storage/v1/object/{TALENT_BUCKET}/{safe_name}",
                    content=data,
                    headers={
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": mime,
                        "x-upsert": "true"
                    }
                )
            if r.status_code in (200, 201):
                return f"{SUPABASE_URL}/storage/v1/object/public/{TALENT_BUCKET}/{safe_name}"
        except Exception as e:
            print(f"[TalentChat] Supabase upload failed: {e}")

    # Fallback — local disk
    path = os.path.join(LOCAL_UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(data)
    return f"/static/uploads/talent_chat/{safe_name}"


# ─── WebSocket connection manager ─────────────────────────────────────────────
@dataclass
class TalentConn:
    websocket: WebSocket
    room_id: str
    sender_type: str   # 'hr' | 'applicant'
    sender_name: str


class TalentChatManager:
    def __init__(self):
        self._rooms: Dict[str, List[TalentConn]] = {}

    async def connect(self, conn: TalentConn):
        await conn.websocket.accept()
        self._rooms.setdefault(conn.room_id, []).append(conn)

    def disconnect(self, ws: WebSocket, room_id: str):
        if room_id in self._rooms:
            self._rooms[room_id] = [c for c in self._rooms[room_id] if c.websocket is not ws]
            if not self._rooms[room_id]:
                del self._rooms[room_id]

    async def broadcast(self, room_id: str, payload: dict, exclude: WebSocket = None):
        for conn in self._rooms.get(room_id, []):
            if conn.websocket is not exclude:
                try:
                    await conn.websocket.send_json(payload)
                except Exception:
                    pass

    def connected_types(self, room_id: str) -> List[str]:
        return [c.sender_type for c in self._rooms.get(room_id, [])]


manager = TalentChatManager()


# ─── Auth helpers ─────────────────────────────────────────────────────────────
async def _resolve_room_by_token(token: str):
    db = get_db()
    res = await db_execute(
        lambda: db.table("talent_chat_rooms").select("*").eq("applicant_token", token).execute()
    )
    if not res.data:
        raise HTTPException(404, "Invalid or expired chat token")
    return res.data[0]


# ─── HR endpoints ─────────────────────────────────────────────────────────────

@router.get("/hr/talent-chat/rooms")
async def list_rooms(current_admin=Depends(require_roles(["admin", "super_admin", "hr", "operations"]))):
    db = get_db()
    res = await db_execute(
        lambda: db.table("talent_chat_rooms")
            .select("*")
            .eq("status", "Active")
            .order("last_message_at", desc=True)
            .execute()
    )
    return res.data or []


@router.post("/hr/talent-chat/rooms")
async def open_room(
    body: dict,
    current_admin=Depends(require_roles(["admin", "super_admin", "hr", "operations"]))
):
    """
    Idempotent — returns existing room if candidate_email already has one.
    Body: { candidate_name, candidate_email, candidate_phone?, source?, role_interest?, candidate_id? }
    """
    db = get_db()
    email = body.get("candidate_email", "").strip().lower()
    if not email:
        raise HTTPException(400, "candidate_email is required")

    # Check existing
    existing = await db_execute(
        lambda: db.table("talent_chat_rooms").select("*").eq("candidate_email", email).execute()
    )
    if existing.data:
        return existing.data[0]

    admin_id = current_admin.get("id") or current_admin.get("sub")
    room = {
        "candidate_name": body.get("candidate_name", "Candidate"),
        "candidate_email": email,
        "candidate_phone": body.get("candidate_phone"),
        "source": body.get("source", "Applied"),
        "role_interest": body.get("role_interest"),
        "created_by_admin_id": admin_id,
    }
    res = await db_execute(lambda: db.table("talent_chat_rooms").insert(room).execute())
    return res.data[0]


@router.get("/hr/talent-chat/rooms/{room_id}/messages")
async def get_messages(
    room_id: str,
    limit: int = Query(60, le=200),
    current_admin=Depends(require_roles(["admin", "super_admin", "hr", "operations"]))
):
    db = get_db()
    res = await db_execute(
        lambda: db.table("talent_chat_messages")
            .select("*")
            .eq("room_id", room_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
    )
    return res.data or []


@router.post("/hr/talent-chat/rooms/{room_id}/messages")
async def hr_send_message(
    room_id: str,
    body: dict,
    background_tasks: BackgroundTasks,
    current_admin=Depends(require_roles(["admin", "super_admin", "hr", "operations"]))
):
    db = get_db()
    room_res = await db_execute(
        lambda: db.table("talent_chat_rooms").select("*").eq("id", room_id).execute()
    )
    if not room_res.data:
        raise HTTPException(404, "Room not found")
    room = room_res.data[0]

    text = body.get("message", "").strip()
    if not text:
        raise HTTPException(400, "message is required")

    sender_name = current_admin.get("full_name") or current_admin.get("email", "HR Team")

    msg = {
        "room_id": room_id,
        "sender_type": "hr",
        "sender_name": sender_name,
        "message": text,
        "message_type": "text",
        "is_read_by_hr": True,
        "is_read_by_applicant": False,
    }
    ins = await db_execute(lambda: db.table("talent_chat_messages").insert(msg).execute())
    new_msg = ins.data[0]

    # Update room metadata
    await db_execute(lambda: db.table("talent_chat_rooms").update({
        "last_message_at": new_msg["created_at"],
        "last_message_preview": text[:80],
        "applicant_unread_count": (room.get("applicant_unread_count") or 0) + 1
    }).eq("id", room_id).execute())

    # Broadcast via WebSocket
    await manager.broadcast(room_id, {"type": "new_message", "message": new_msg})

    return new_msg


@router.post("/hr/talent-chat/rooms/{room_id}/upload")
async def hr_upload_file(
    room_id: str,
    file: UploadFile = File(...),
    current_admin=Depends(require_roles(["admin", "super_admin", "hr", "operations"]))
):
    db = get_db()
    room_res = await db_execute(
        lambda: db.table("talent_chat_rooms").select("*").eq("id", room_id).execute()
    )
    if not room_res.data:
        raise HTTPException(404, "Room not found")
    room = room_res.data[0]

    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 20 MB)")

    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    url = await _store_file(data, file.filename, mime)

    sender_name = current_admin.get("full_name") or current_admin.get("email", "HR Team")
    msg = {
        "room_id": room_id,
        "sender_type": "hr",
        "sender_name": sender_name,
        "message": None,
        "message_type": "file",
        "file_url": url,
        "file_name": file.filename,
        "file_size": len(data),
        "file_mime": mime,
        "is_read_by_hr": True,
        "is_read_by_applicant": False,
    }
    ins = await db_execute(lambda: db.table("talent_chat_messages").insert(msg).execute())
    new_msg = ins.data[0]

    await db_execute(lambda: db.table("talent_chat_rooms").update({
        "last_message_at": new_msg["created_at"],
        "last_message_preview": f"📎 {file.filename}",
        "applicant_unread_count": (room.get("applicant_unread_count") or 0) + 1
    }).eq("id", room_id).execute())

    await manager.broadcast(room_id, {"type": "new_message", "message": new_msg})
    return new_msg


@router.patch("/hr/talent-chat/rooms/{room_id}/read")
async def hr_mark_read(
    room_id: str,
    current_admin=Depends(require_roles(["admin", "super_admin", "hr", "operations"]))
):
    db = get_db()
    await db_execute(
        lambda: db.table("talent_chat_messages")
            .update({"is_read_by_hr": True})
            .eq("room_id", room_id)
            .eq("sender_type", "applicant")
            .execute()
    )
    await db_execute(
        lambda: db.table("talent_chat_rooms").update({"hr_unread_count": 0}).eq("id", room_id).execute()
    )
    return {"ok": True}


# ─── Applicant public endpoints (token-based) ─────────────────────────────────

@router.get("/talent-chat/portal/{token}", response_class=HTMLResponse)
async def applicant_portal(token: str):
    """Serve a lightweight chat page for the applicant (no React needed)."""
    room = await _resolve_room_by_token(token)
    base_url = os.getenv("BASE_URL", "")
    return _applicant_portal_html(room, token, base_url)


@router.get("/talent-chat/{token}/messages")
async def applicant_get_messages(token: str, limit: int = Query(60, le=200)):
    room = await _resolve_room_by_token(token)
    db = get_db()
    res = await db_execute(
        lambda: db.table("talent_chat_messages")
            .select("*")
            .eq("room_id", room["id"])
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
    )
    return res.data or []


@router.post("/talent-chat/{token}/messages")
async def applicant_send_message(token: str, body: dict):
    room = await _resolve_room_by_token(token)
    db = get_db()
    text = body.get("message", "").strip()
    if not text:
        raise HTTPException(400, "message required")

    msg = {
        "room_id": room["id"],
        "sender_type": "applicant",
        "sender_name": room["candidate_name"],
        "message": text,
        "message_type": "text",
        "is_read_by_hr": False,
        "is_read_by_applicant": True,
    }
    ins = await db_execute(lambda: db.table("talent_chat_messages").insert(msg).execute())
    new_msg = ins.data[0]
    now = new_msg["created_at"]

    await db_execute(lambda: db.table("talent_chat_rooms").update({
        "last_message_at": now,
        "last_message_preview": text[:80],
        "hr_unread_count": (room.get("hr_unread_count") or 0) + 1,
        "last_applicant_reply_at": now,
        "followup_email_sent_at": None,   # reset follow-up timer on reply
    }).eq("id", room["id"]).execute())

    await manager.broadcast(room["id"], {"type": "new_message", "message": new_msg})
    return new_msg


@router.post("/talent-chat/{token}/upload")
async def applicant_upload_file(token: str, file: UploadFile = File(...)):
    room = await _resolve_room_by_token(token)
    db = get_db()

    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 20 MB)")

    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    url = await _store_file(data, file.filename, mime)

    msg = {
        "room_id": room["id"],
        "sender_type": "applicant",
        "sender_name": room["candidate_name"],
        "message": None,
        "message_type": "file",
        "file_url": url,
        "file_name": file.filename,
        "file_size": len(data),
        "file_mime": mime,
        "is_read_by_hr": False,
        "is_read_by_applicant": True,
    }
    ins = await db_execute(lambda: db.table("talent_chat_messages").insert(msg).execute())
    new_msg = ins.data[0]

    await db_execute(lambda: db.table("talent_chat_rooms").update({
        "last_message_at": new_msg["created_at"],
        "last_message_preview": f"📎 {file.filename}",
        "hr_unread_count": (room.get("hr_unread_count") or 0) + 1,
        "last_applicant_reply_at": new_msg["created_at"],
        "followup_email_sent_at": None,
    }).eq("id", room["id"]).execute())

    await manager.broadcast(room["id"], {"type": "new_message", "message": new_msg})
    return new_msg


@router.patch("/talent-chat/{token}/read")
async def applicant_mark_read(token: str):
    room = await _resolve_room_by_token(token)
    db = get_db()
    await db_execute(
        lambda: db.table("talent_chat_messages")
            .update({"is_read_by_applicant": True})
            .eq("room_id", room["id"])
            .eq("sender_type", "hr")
            .execute()
    )
    await db_execute(
        lambda: db.table("talent_chat_rooms").update({"applicant_unread_count": 0}).eq("id", room["id"]).execute()
    )
    return {"ok": True}


# ─── WebSocket ────────────────────────────────────────────────────────────────

async def _ping_loop(ws: WebSocket):
    try:
        while True:
            await asyncio.sleep(25)
            await ws.send_json({"type": "ping"})
    except Exception:
        pass


@router.websocket("/ws/talent-chat/{room_id}")
async def talent_chat_ws(websocket: WebSocket, room_id: str, token: str = Query(...)):
    """
    token is either:
      - An admin JWT (verified via same secret as auth.py)
      - An applicant_token UUID (checked against talent_chat_rooms)
    """
    db = get_db()
    sender_type = None
    sender_name = "Unknown"

    # Try applicant token first (UUID format)
    try:
        uuid.UUID(token)          # raises if not a UUID
        room_res = await db_execute(
            lambda: db.table("talent_chat_rooms")
                .select("id, candidate_name, applicant_token")
                .eq("id", room_id)
                .eq("applicant_token", token)
                .execute()
        )
        if room_res.data:
            sender_type = "applicant"
            sender_name = room_res.data[0]["candidate_name"]
    except ValueError:
        pass

    if sender_type is None:
        # Try admin JWT
        import jwt as pyjwt
        try:
            secret = os.getenv("JWT_SECRET", "eximp-cloves-secret-key-change-in-production")
            payload = pyjwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
            sender_type = "hr"
            sender_name = payload.get("full_name") or payload.get("email", "HR Team")
        except Exception:
            await websocket.close(code=4001)
            return

    conn = TalentConn(websocket=websocket, room_id=room_id,
                      sender_type=sender_type, sender_name=sender_name)
    await manager.connect(conn)
    ping_task = asyncio.create_task(_ping_loop(websocket))

    # Tell the room who just connected
    await manager.broadcast(room_id, {"type": "presence", "sender_type": sender_type, "online": True})

    try:
        while True:
            raw = await websocket.receive_text()
            if raw == "pong":
                continue
            data = json.loads(raw)
            # Typing indicator or other client signals — just fan out
            await manager.broadcast(room_id, data, exclude=websocket)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[TalentChat WS] {e}")
    finally:
        manager.disconnect(websocket, room_id)
        ping_task.cancel()
        await manager.broadcast(room_id, {"type": "presence", "sender_type": sender_type, "online": False})


# ─── 1-hour follow-up email scheduler ────────────────────────────────────────

@router.post("/hr/talent-chat/check-followups")
async def check_followups(
    background_tasks: BackgroundTasks,
    current_admin=Depends(require_roles(["admin", "super_admin"]))
):
    """
    Called by the scheduler every 10 minutes.
    Finds rooms where:
      - HR has sent at least one message
      - The applicant has NOT replied in the last 60 minutes
      - A follow-up email has not already been sent for this gap
    """
    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    rooms_res = await db_execute(
        lambda: db.table("talent_chat_rooms")
            .select("id, candidate_name, candidate_email, applicant_token, last_message_at, last_applicant_reply_at, followup_email_sent_at")
            .eq("status", "Active")
            .execute()
    )
    rooms = rooms_res.data or []
    sent = 0
    base_url = os.getenv("BASE_URL", "https://app.eximps-cloves.com")

    for room in rooms:
        last_msg = room.get("last_message_at")
        last_reply = room.get("last_applicant_reply_at")
        followup_sent = room.get("followup_email_sent_at")

        if not last_msg:
            continue

        # Has been more than 1 hour since last HR message?
        if last_msg > cutoff:
            continue  # recent — not yet

        # Applicant hasn't replied (or replied before the last HR msg)
        if last_reply and last_reply >= last_msg:
            continue  # they replied

        # Already sent a follow-up for this gap?
        if followup_sent and followup_sent >= last_msg:
            continue

        # Send follow-up
        chat_url = f"{base_url}/talent-chat/portal/{room['applicant_token']}"
        background_tasks.add_task(
            _send_followup_email,
            room["candidate_email"],
            room["candidate_name"],
            chat_url
        )

        await db_execute(lambda: db.table("talent_chat_rooms").update({
            "followup_email_sent_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", room["id"]).execute())
        sent += 1

    return {"checked": len(rooms), "followups_sent": sent}


async def _send_followup_email(email: str, name: str, chat_url: str):
    """Thin wrapper — delegates to email_service."""
    try:
        from email_service import send_talent_chat_followup_email
        await send_talent_chat_followup_email(email, name, chat_url)
    except Exception as e:
        print(f"[TalentChat Follow-up] Failed for {email}: {e}")


# ─── Applicant portal HTML ────────────────────────────────────────────────────

def _applicant_portal_html(room: dict, token: str, base_url: str) -> str:
    ws_protocol = "wss" if "https" in base_url else "ws"
    ws_host = base_url.replace("https://", "").replace("http://", "") or "localhost:8000"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Chat with Eximp & Cloves HR — {room['candidate_name']}</title>
<style>
  :root{{--gold:#C47D0A;--bg:#0B0C0F;--surface:#111317;--card:#1A1D24;--border:#2D2F36;--text:#E5E7EB;--sub:#A0A0A0;--muted:#6B7280;}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);height:100dvh;display:flex;flex-direction:column;}}
  header{{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;align-items:center;gap:14px;}}
  .av{{width:42px;height:42px;border-radius:50%;background:#C47D0A22;border:1.5px solid #C47D0A44;display:flex;align-items:center;justify-content:center;font-weight:800;color:var(--gold);font-size:18px;flex-shrink:0;}}
  .av-name{{font-weight:700;font-size:15px;}}
  .av-sub{{font-size:12px;color:var(--sub);}}
  #msgs{{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:10px;}}
  .bubble{{max-width:70%;padding:10px 14px;border-radius:14px;font-size:14px;line-height:1.5;word-break:break-word;}}
  .bubble.hr{{align-self:flex-start;background:var(--card);border:1px solid var(--border);border-bottom-left-radius:4px;}}
  .bubble.me{{align-self:flex-end;background:#C47D0A22;border:1px solid #C47D0A33;border-bottom-right-radius:4px;}}
  .bubble .ts{{font-size:10px;color:var(--muted);margin-top:4px;text-align:right;}}
  .bubble .sender{{font-size:10px;color:var(--gold);font-weight:700;margin-bottom:4px;}}
  .file-thumb{{max-width:220px;border-radius:8px;margin-top:6px;cursor:pointer;}}
  .file-link{{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:12px;color:var(--text);text-decoration:none;margin-top:6px;}}
  footer{{background:var(--surface);border-top:1px solid var(--border);padding:12px 16px;display:flex;gap:10px;align-items:flex-end;}}
  #msgInput{{flex:1;background:var(--card);border:1px solid var(--border);border-radius:10px;color:var(--text);padding:10px 14px;font-size:14px;resize:none;max-height:120px;outline:none;}}
  #msgInput:focus{{border-color:var(--gold);}}
  .btn{{background:#C47D0A;color:#fff;border:none;border-radius:10px;padding:10px 18px;font-size:14px;font-weight:700;cursor:pointer;flex-shrink:0;}}
  .btn:disabled{{opacity:.5;cursor:default;}}
  .btn.sec{{background:transparent;border:1px solid var(--border);color:var(--sub);}}
  .typing{{font-size:12px;color:var(--muted);padding:0 20px 4px;}}
  #fileInput{{display:none;}}
  .pdf-frame{{width:100%;height:360px;border-radius:8px;border:1px solid var(--border);margin-top:6px;}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
</head>
<body>
<header>
  <div class="av">E</div>
  <div>
    <div class="av-name">Eximp & Cloves — HR Team</div>
    <div class="av-sub">Talent Pool Chat · {room['candidate_name']}</div>
  </div>
</header>
<div id="msgs"><div style="text-align:center;color:var(--muted);font-size:13px;padding:30px">Loading messages…</div></div>
<div class="typing" id="typingBar"></div>
<footer>
  <label for="fileInput" class="btn sec" style="padding:10px 12px;cursor:pointer" title="Attach file">📎</label>
  <input id="fileInput" type="file" accept="*/*"/>
  <textarea id="msgInput" rows="1" placeholder="Type a message…"></textarea>
  <button class="btn" id="sendBtn" onclick="sendMsg()">Send</button>
</footer>
<script>
const TOKEN = "{token}";
const ROOM_ID = "{room['id']}";
const MY_NAME = "{room['candidate_name']}";
const API = "/api/talent-chat/" + TOKEN;
let ws = null; let typing = false; let typingTimeout;

const msgsEl = document.getElementById("msgs");
const inputEl = document.getElementById("msgInput");
const typingBar = document.getElementById("typingBar");

function fmt(ts){{const d=new Date(ts);return d.toLocaleTimeString([],{{hour:"2-digit",minute:"2-digit"}});}}
function formatSize(b){{if(b<1024)return b+"B";if(b<1048576)return(b/1024).toFixed(1)+"KB";return(b/1048576).toFixed(1)+"MB";}}

function renderFile(msg){{
  const mime=msg.file_mime||"";
  if(mime.startsWith("image/"))
    return `<img src="${{msg.file_url}}" class="file-thumb" onclick="window.open('${{msg.file_url}}','_blank')" alt="${{msg.file_name}}"/>`;
  if(mime==="application/pdf")
    return `<embed src="${{msg.file_url}}" type="application/pdf" class="pdf-frame"/>
            <a href="${{msg.file_url}}" target="_blank" class="file-link">⬇ Open PDF</a>`;
  return `<a href="${{msg.file_url}}" target="_blank" class="file-link">📎 ${{msg.file_name}} (${{formatSize(msg.file_size||0)}})</a>`;
}}

function addBubble(msg){{
  const isMe = msg.sender_type==="applicant";
  const div=document.createElement("div");
  div.className="bubble "+(isMe?"me":"hr");
  div.dataset.id=msg.id;
  let body="";
  if(!isMe) body+=`<div class="sender">${{msg.sender_name}}</div>`;
  if(msg.message) body+=`<div>${{msg.message.replace(/</g,"&lt;")}}</div>`;
  if(msg.message_type==="file") body+=renderFile(msg);
  body+=`<div class="ts">${{fmt(msg.created_at)}}</div>`;
  div.innerHTML=body;
  msgsEl.appendChild(div);
  msgsEl.scrollTop=msgsEl.scrollHeight;
}}

async function loadHistory(){{
  msgsEl.innerHTML="";
  const res=await fetch(API+"/messages");
  const msgs=await res.json();
  msgs.forEach(addBubble);
  // Mark read
  fetch(API+"/read",{{method:"PATCH"}});
}}

function connectWS(){{
  const proto=location.protocol==="https:"?"wss":"ws";
  ws=new WebSocket(`${{proto}}://${{location.host}}/api/ws/talent-chat/${{ROOM_ID}}?token=${{TOKEN}}`);
  ws.onmessage=e=>{{
    const data=JSON.parse(e.data);
    if(data.type==="ping") return ws.send(JSON.stringify({{type:"pong"}}));
    if(data.type==="new_message"){{
      if(!document.querySelector(`[data-id="${{data.message.id}}"]`)) addBubble(data.message);
      fetch(API+"/read",{{method:"PATCH"}});
    }}
    if(data.type==="typing" && data.sender_type==="hr"){{
      typingBar.textContent="HR is typing…";
      clearTimeout(typingTimeout);
      typingTimeout=setTimeout(()=>{{typingBar.textContent="";}},2500);
    }}
  }};
  ws.onclose=()=>setTimeout(connectWS,3000);
}}

async function sendMsg(){{
  const text=inputEl.value.trim();
  if(!text) return;
  inputEl.value=""; inputEl.style.height="";
  const btn=document.getElementById("sendBtn");
  btn.disabled=true;
  try{{
    const res=await fetch(API+"/messages",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{message:text}})}});
    const msg=await res.json();
    addBubble(msg);
  }} finally {{ btn.disabled=false; }}
}}

document.getElementById("fileInput").addEventListener("change",async e=>{{
  const file=e.target.files[0]; if(!file) return;
  const fd=new FormData(); fd.append("file",file);
  const res=await fetch(API+"/upload",{{method:"POST",body:fd}});
  const msg=await res.json();
  addBubble(msg);
  e.target.value="";
}});

inputEl.addEventListener("keydown",e=>{{
  if(e.key==="Enter"&&!e.shiftKey){{e.preventDefault();sendMsg();}}
}});
inputEl.addEventListener("input",()=>{{
  inputEl.style.height="auto"; inputEl.style.height=inputEl.scrollHeight+"px";
  if(!typing){{typing=true;ws&&ws.readyState===1&&ws.send(JSON.stringify({{type:"typing",sender_type:"applicant"}}));}}
  clearTimeout(typingTimeout);
  typingTimeout=setTimeout(()=>{{typing=false;}},1500);
}});

loadHistory();
connectWS();
</script>
</body>
</html>"""
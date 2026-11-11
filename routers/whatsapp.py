# -*- coding: utf-8 -*-
"""
WhatsApp Support Line Gateway Router
Communicates with local Baileys Node.js gateway (http://127.0.0.1:8005)
Supports multi-device pairing via QR code, Cloudinary session backup, and direct message dispatch.
"""

import os
import shutil
import subprocess
import logging
import urllib.request
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from routers.auth import verify_token, has_any_role

logger = logging.getLogger(__name__)

router = APIRouter()

WHATSAPP_GATEWAY_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://127.0.0.1:8005")
_gateway_process = None


def start_whatsapp_gateway_process():
    """
    Auto-spawns the Baileys Node.js WhatsApp Gateway service on port 8005 if not already running.
    Ensures seamless execution on both localhost and cloud environments like Render.
    """
    global _gateway_process
    if _gateway_process is not None and _gateway_process.poll() is None:
        return

    # Check if gateway is already answering on WHATSAPP_GATEWAY_URL
    try:
        req = urllib.request.Request(f"{WHATSAPP_GATEWAY_URL}/health", headers={"User-Agent": "FastAPI"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                return
    except Exception:
        pass

    service_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "whatsapp-service")
    server_js = os.path.join(service_dir, "server.js")
    if not os.path.exists(server_js):
        logger.warning(f"[WhatsApp Gateway] server.js not found at {server_js}")
        return

    node_bin = shutil.which("node")
    if not node_bin:
        for candidate in ["/usr/bin/node", "/usr/local/bin/node", "/opt/render/project/.render/node/bin/node"]:
            if os.path.exists(candidate):
                node_bin = candidate
                break

    if not node_bin:
        logger.warning("[WhatsApp Gateway] Node.js binary not found on PATH. Start gateway manually on port 8005.")
        return

    try:
        logger.info(f"[WhatsApp Gateway] Spawning WhatsApp Gateway sidecar ({node_bin} server.js)...")
        _gateway_process = subprocess.Popen(
            [node_bin, "server.js"],
            cwd=service_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"[WhatsApp Gateway] Sidecar process started (PID {_gateway_process.pid})")
    except Exception as e:
        logger.warning(f"[WhatsApp Gateway] Could not spawn gateway sidecar: {e}")


def stop_whatsapp_gateway_process():
    """Gracefully shuts down the gateway sidecar process if managed by Python."""
    global _gateway_process
    if _gateway_process is not None and _gateway_process.poll() is None:
        try:
            logger.info(f"[WhatsApp Gateway] Stopping sidecar process (PID {_gateway_process.pid})...")
            _gateway_process.terminate()
            _gateway_process.wait(timeout=3)
        except Exception:
            try:
                _gateway_process.kill()
            except Exception:
                pass
        _gateway_process = None


async def send_whatsapp_message(phone: str, message: str, media_url: str = None) -> dict:
    """
    Internal helper to send a WhatsApp message to any phone number from the linked support line.
    """
    if not phone or not message:
        return {"success": False, "error": "Phone and message required"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{WHATSAPP_GATEWAY_URL}/api/whatsapp/send",
                json={"phone": phone, "message": message, "mediaUrl": media_url},
            )
            data = resp.json()
            return data
    except Exception as e:
        logger.warning(f"[WhatsApp Gateway] Dispatch error to {phone}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/status")
async def get_whatsapp_status(request: Request, current_user=Depends(verify_token)):
    """
    Retrieves the current connection status of the WhatsApp Support Line.
    Returns status: 'connected' | 'connecting' | 'disconnected', qrCode, user phone.
    """
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"{WHATSAPP_GATEWAY_URL}/api/whatsapp/status")
            return resp.json()
    except Exception as e:
        logger.warning(f"[WhatsApp Gateway] Could not reach gateway service: {e}")
        start_whatsapp_gateway_process()
        return {
            "status": "disconnected",
            "qrCode": None,
            "user": None,
            "authExists": False,
            "serviceOnline": False,
            "error": "WhatsApp Gateway service starting up. Please refresh in a moment.",
        }


@router.post("/connect")
async def connect_whatsapp(request: Request, current_user=Depends(verify_token)):
    """
    Initiates WhatsApp socket connection and generates a live pairing QR code.
    Requires Admin or Super Admin role.
    """
    if not has_any_role(current_user, "admin", "super_admin", "superadmin", "operations"):
        raise HTTPException(status_code=403, detail="Admin permissions required")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{WHATSAPP_GATEWAY_URL}/api/whatsapp/connect")
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with WhatsApp gateway: {e}")


@router.post("/disconnect")
async def disconnect_whatsapp(request: Request, current_user=Depends(verify_token)):
    """
    Unlinks the current WhatsApp Support Line and wipes local/cloud session data.
    Requires Super Admin role.
    """
    if not has_any_role(current_user, "admin", "super_admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Super Admin permissions required")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{WHATSAPP_GATEWAY_URL}/api/whatsapp/disconnect")
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with WhatsApp gateway: {e}")


@router.post("/send-test")
async def send_test_whatsapp(request: Request, current_user=Depends(verify_token)):
    """
    Sends a test message to verify the connected WhatsApp Support Line.
    """
    data = await request.json()
    phone = data.get("phone")
    message = data.get("message", "Hello! This is a verified test message from Eximp & Cloves Support Line.")

    result = await send_whatsapp_message(phone, message)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Message failed to send"))
    return result


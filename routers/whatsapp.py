# -*- coding: utf-8 -*-
"""
WhatsApp Support Line Gateway Router
Communicates with local Baileys Node.js gateway (http://127.0.0.1:8005)
Supports multi-device pairing via QR code, Cloudinary session backup, and direct message dispatch.
"""

import os
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from routers.auth import verify_token, has_any_role

logger = logging.getLogger(__name__)

router = APIRouter()

WHATSAPP_GATEWAY_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://127.0.0.1:8005")


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
        return {
            "status": "disconnected",
            "qrCode": None,
            "user": None,
            "authExists": False,
            "serviceOnline": False,
            "error": "WhatsApp Gateway service offline. Start gateway node service on port 8005.",
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


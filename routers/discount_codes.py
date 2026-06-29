from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.encoders import jsonable_encoder
from models import DiscountCodeCreate, DiscountCodeResponse, DiscountCodeValidateResponse
from database import get_db, db_execute
from routers.auth import verify_token
from datetime import datetime
import random
import string
from decimal import Decimal
from typing import Optional, List

router = APIRouter()

def generate_random_code(length=6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "EXIMP-" + "".join(random.choice(chars) for _ in range(length))

@router.post("/", response_model=DiscountCodeResponse)
async def create_discount_code(data: DiscountCodeCreate, current_admin=Depends(verify_token)):
    db = get_db()
    
    # 1. Authorize: Admin only
    roles = {r.strip().lower() for r in (current_admin.get("role") or "").split(",")}
    if not (roles & {"admin", "super_admin"}):
        raise HTTPException(status_code=403, detail="Only admins can generate discount codes")
        
    code_str = (data.code or "").strip().upper()
    if not code_str:
        # Loop until unique code is generated
        for _ in range(10):
            temp_code = generate_random_code()
            check_res = await db_execute(lambda: db.table("discount_codes").select("id").eq("code", temp_code).execute())
            if not check_res.data:
                code_str = temp_code
                break
        if not code_str:
            raise HTTPException(status_code=500, detail="Failed to generate a unique discount code")
    else:
        # Check uniqueness
        check_res = await db_execute(lambda: db.table("discount_codes").select("id").eq("code", code_str).execute())
        if check_res.data:
            raise HTTPException(status_code=400, detail=f"Discount code '{code_str}' already exists")

    insert_data = {
        "code": code_str,
        "discount_type": data.discount_type.lower(),
        "discount_value": float(data.discount_value),
        "is_active": data.is_active,
        "max_uses": data.max_uses,
        "uses_count": 0,
        "expires_at": data.expires_at.isoformat() if data.expires_at else None,
        "created_by": current_admin.get("sub")
    }

    res = await db_execute(lambda: db.table("discount_codes").insert(insert_data).execute())
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create discount code")
        
    return res.data[0]

@router.get("/", response_model=List[DiscountCodeResponse])
async def list_discount_codes(current_admin=Depends(verify_token)):
    db = get_db()
    
    # 1. Authorize: Admin only
    roles = {r.strip().lower() for r in (current_admin.get("role") or "").split(",")}
    if not (roles & {"admin", "super_admin"}):
        raise HTTPException(status_code=403, detail="Access denied")
        
    res = await db_execute(lambda: db.table("discount_codes").select("*").order("created_at", desc=True).execute())
    return res.data or []

@router.patch("/{code_id}", response_model=DiscountCodeResponse)
async def update_discount_code(code_id: str, payload: dict, current_admin=Depends(verify_token)):
    db = get_db()
    
    # 1. Authorize: Admin only
    roles = {r.strip().lower() for r in (current_admin.get("role") or "").split(",")}
    if not (roles & {"admin", "super_admin"}):
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Whitelist updates
    allowed = {}
    if "is_active" in payload:
        allowed["is_active"] = bool(payload["is_active"])
    if "max_uses" in payload:
        allowed["max_uses"] = int(payload["max_uses"]) if payload["max_uses"] is not None else None
    if "expires_at" in payload:
        allowed["expires_at"] = payload["expires_at"]

    if not allowed:
        raise HTTPException(status_code=400, detail="No fields to update")

    res = await db_execute(lambda: db.table("discount_codes").update(allowed).eq("id", code_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Discount code not found")
        
    return res.data[0]

@router.delete("/{code_id}")
async def delete_discount_code(code_id: str, current_admin=Depends(verify_token)):
    db = get_db()
    
    # 1. Authorize: Admin only
    roles = {r.strip().lower() for r in (current_admin.get("role") or "").split(",")}
    if not (roles & {"admin", "super_admin"}):
        raise HTTPException(status_code=403, detail="Access denied")
        
    res = await db_execute(lambda: db.table("discount_codes").delete().eq("id", code_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Discount code not found")
        
    return {"status": "success", "message": "Discount code deleted"}

@router.get("/validate", response_model=DiscountCodeValidateResponse)
async def validate_discount_code(
    code: str = Query(..., min_length=1),
    total_amount: Optional[Decimal] = Query(None)
):
    db = get_db()
    code_str = code.strip().upper()
    
    res = await db_execute(lambda: db.table("discount_codes").select("*").eq("code", code_str).execute())
    if not res.data:
        return {
            "valid": False,
            "message": "Invalid discount code."
        }
        
    code_record = res.data[0]
    
    # Check if active
    if not code_record.get("is_active", True):
        return {
            "valid": False,
            "message": "This discount code is inactive."
        }
        
    # Check expiry
    expires_at_str = code_record.get("expires_at")
    if expires_at_str:
        try:
            # Parse ISO timestamp
            # Remove Z or replace timezone for python comparison
            t_str = expires_at_str.replace("Z", "+00:00")
            expires_at = datetime.fromisoformat(t_str)
            # Make sure now is tz-aware too
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if expires_at < now:
                return {
                    "valid": False,
                    "message": "This discount code has expired."
                }
        except Exception:
            pass
            
    # Check usage limit
    max_uses = code_record.get("max_uses")
    uses_count = code_record.get("uses_count", 0)
    if max_uses is not None and uses_count >= max_uses:
        return {
            "valid": False,
            "message": "This discount code has reached its usage limit."
        }
        
    # Valid! Calculate discount amount if total_amount is passed
    discount_amount = Decimal("0.00")
    discount_val = Decimal(str(code_record.get("discount_value") or 0))
    discount_type = code_record.get("discount_type", "percentage")
    
    if total_amount is not None:
        if discount_type == "percentage":
            discount_amount = total_amount * discount_val / Decimal("100")
        else: # flat
            discount_amount = min(discount_val, total_amount)
            
    return {
        "valid": True,
        "message": "Discount code applied successfully.",
        "discount_type": discount_type,
        "discount_value": discount_val,
        "discount_amount": discount_amount
    }

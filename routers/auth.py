from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import bcrypt
import os
from datetime import datetime, timedelta
from models import (
    AdminLogin, AdminCreate, TokenResponse,
    ChangePasswordRequest, ResetPasswordRequest, UpdateProfileRequest
)
from database import get_db

router = APIRouter()
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET", "eximp-cloves-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def has_any_role(admin_payload: dict, *roles: str) -> bool:
    """Check if the admin has any of the given roles (supports comma-separated multi-role)."""
    user_roles = {r.strip() for r in (admin_payload.get("role") or "").split(",") if r.strip()}
    return bool(user_roles & set(roles))


# Alias for dependency consistency
get_current_admin = verify_token

def resolve_admin_token(token: str = None, authorization: str = Header(None)):
    """
    Dependency that resolves the admin payload from either:
    1. Authorization: Bearer <token> header
    2. token=<token> query parameter
    """
    if authorization:
        try:
            scheme, creds = authorization.split()
            if scheme.lower() == "bearer":
                return verify_token(HTTPAuthorizationCredentials(scheme=scheme, credentials=creds))
        except Exception:
            pass
    
    if token:
        try:
            return verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
        except Exception:
            pass
            
    raise HTTPException(status_code=401, detail="Not authenticated")


# LOGIN
@router.post("/login", response_model=TokenResponse)
async def login(data: AdminLogin):
    db = get_db()
    result = db.table("admins").select("*").eq("email", data.email).eq("is_active", True).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    admin = result.data[0]
    if not bcrypt.checkpw(data.password.encode(), admin["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if admin.get("is_archived"):
        raise HTTPException(status_code=403, detail="This account has been archived")
    token = create_token({"sub": admin["id"], "email": admin["email"], "role": admin["role"], "primary_role": admin.get("primary_role", "staff")})
    return {
        "access_token": token,
        "admin": {
            "id": admin["id"], 
            "name": admin["full_name"], 
            "email": admin["email"], 
            "role": admin["role"],
            "primary_role": admin.get("primary_role", "staff")
        }
    }


# GET CURRENT USER
@router.get("/me")
async def me(current_admin=Depends(verify_token)):
    db = get_db()
    result = db.table("admins").select("id, full_name, email, role, primary_role, created_at").eq("id", current_admin["sub"]).execute()
    return result.data[0] if result.data else {}


# CREATE TEAM MEMBER (admin only)
@router.post("/register")
async def register(data: AdminCreate, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Only admins can create accounts")
    db = get_db()
    existing = db.table("admins").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    result = db.table("admins").insert({
        "full_name": data.full_name, "email": data.email,
        "password_hash": password_hash, "role": data.role,
        "primary_role": data.primary_role,
        "is_active": True, "is_archived": False,
    }).execute()
    return {"message": "Account created successfully", "id": result.data[0]["id"]}


# LIST ALL TEAM MEMBERS (admin only)
@router.get("/admins")
async def list_admins(current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admins only")
    db = get_db()
    result = db.table("admins").select("id, full_name, email, role, primary_role, is_active, is_archived, created_at").order("created_at").execute()
    return result.data


def require_roles(allowed_roles: list[str]):
    """
    Returns a dependency that checks if the current user has any of the required roles.
    """
    async def role_checker(current_admin=Depends(verify_token)):
        user_roles = [r.strip() for r in current_admin.get("role", "").split(",")]
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_admin
    return role_checker


# UPDATE OWN PROFILE
@router.patch("/me/profile")
async def update_profile(data: UpdateProfileRequest, current_admin=Depends(verify_token)):
    if not data.full_name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    db = get_db()
    db.table("admins").update({"full_name": data.full_name.strip()}).eq("id", current_admin["sub"]).execute()
    return {"message": "Profile updated", "full_name": data.full_name.strip()}


# CHANGE OWN PASSWORD
@router.patch("/me/password")
async def change_password(data: ChangePasswordRequest, current_admin=Depends(verify_token)):
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    db = get_db()
    result = db.table("admins").select("password_hash").eq("id", current_admin["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")
    if not bcrypt.checkpw(data.current_password.encode(), result.data[0]["password_hash"].encode()):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    new_hash = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
    db.table("admins").update({"password_hash": new_hash}).eq("id", current_admin["sub"]).execute()
    return {"message": "Password changed successfully"}


# RESET ANOTHER USER'S PASSWORD (admin only)
@router.patch("/admins/{admin_id}/reset-password")
async def reset_password(admin_id: str, data: ResetPasswordRequest, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admins only")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    db = get_db()
    target = db.table("admins").select("id, full_name").eq("id", admin_id).execute()
    if not target.data:
        raise HTTPException(status_code=404, detail="Account not found")
    new_hash = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
    db.table("admins").update({"password_hash": new_hash}).eq("id", admin_id).execute()
    return {"message": f"Password reset for {target.data[0]['full_name']}"}


# DEACTIVATE (admin only)
@router.patch("/admins/{admin_id}/deactivate")
async def deactivate_admin(admin_id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admins only")
    if current_admin.get("sub") == admin_id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    db = get_db()
    result = db.table("admins").update({"is_active": False}).eq("id", admin_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account deactivated"}


# REACTIVATE (admin only)
@router.patch("/admins/{admin_id}/reactivate")
async def reactivate_admin(admin_id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admins only")
    db = get_db()
    result = db.table("admins").update({"is_active": True, "is_archived": False}).eq("id", admin_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account reactivated"}


# ARCHIVE (admin only)
@router.patch("/admins/{admin_id}/archive")
async def archive_admin(admin_id: str, current_admin=Depends(verify_token)):
    if not has_any_role(current_admin, "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admins only")
    if current_admin.get("sub") == admin_id:
        raise HTTPException(status_code=400, detail="You cannot archive your own account")
    db = get_db()
    target = db.table("admins").select("id, full_name").eq("id", admin_id).execute()
    if not target.data:
        raise HTTPException(status_code=404, detail="Account not found")
    db.table("admins").update({"is_active": False, "is_archived": True}).eq("id", admin_id).execute()
    return {"message": f"{target.data[0]['full_name']} has been archived"}


# UPDATE ROLES (admin/super_admin only)
@router.patch("/admins/{admin_id}/roles")
async def update_admin_roles(admin_id: str, data: dict, current_admin=Depends(verify_token)):
    current_roles = (current_admin.get("role") or "").split(",")
    if not any(r.strip() in ["admin", "super_admin"] for r in current_roles):
        raise HTTPException(status_code=403, detail="Admins only")
    if current_admin.get("sub") == admin_id:
        raise HTTPException(status_code=400, detail="Use 'My Profile' to change your own roles")

    role = data.get("role", "").strip()
    primary_role = data.get("primary_role", "staff").strip()

    if not role:
        raise HTTPException(status_code=400, detail="At least one role is required")

    db = get_db()
    target = db.table("admins").select("id, full_name").eq("id", admin_id).execute()
    if not target.data:
        raise HTTPException(status_code=404, detail="Account not found")

    db.table("admins").update({"role": role, "primary_role": primary_role}).eq("id", admin_id).execute()
    return {"message": f"Roles updated for {target.data[0]['full_name']}"}

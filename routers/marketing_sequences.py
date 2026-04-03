from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from database import get_db
from routers.auth import verify_token

router = APIRouter()

@router.get("/")
async def list_sequences(current_admin=Depends(verify_token)):
    # Placeholder for PRD 10 (Automated sequences)
    return []

@router.post("/")
async def create_sequence(current_admin=Depends(verify_token)):
    # Placeholder
    return {"message": "Sequences are currently in development."}

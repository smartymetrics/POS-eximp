from fastapi import FastAPI
from database import supabase
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Init DB")
    try:
        result = supabase.table("admins").select("id").limit(1).execute()
        print("DB OK")
    except Exception as e:
        print(f"DB error: {e}")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}
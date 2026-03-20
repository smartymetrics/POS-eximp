import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# ── Validate env vars are present before anything else runs ──
if not SUPABASE_URL:
    print("❌ ERROR: SUPABASE_URL is not set in your .env file")
    sys.exit(1)

if not SUPABASE_SERVICE_KEY:
    print("❌ ERROR: SUPABASE_SERVICE_KEY is not set in your .env file")
    sys.exit(1)

if not SUPABASE_URL.startswith("https://"):
    print("❌ ERROR: SUPABASE_URL must start with https://")
    sys.exit(1)

# ── Only the service_role key should be used here ──
# The anon/publishable key has restricted permissions
# and will cause silent failures on protected tables.
if "anon" in SUPABASE_SERVICE_KEY.lower() or len(SUPABASE_SERVICE_KEY) < 50:
    print("❌ ERROR: You appear to be using the anon (public) key or a placeholder.")
    print("   Please use the SECRET SERVICE ROLE KEY from your Supabase Project Settings.")
    sys.exit(1)

# ── Initialise the Supabase client (modern SDK >= 2.10) ──────
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
except Exception as e:
    print(f"❌ ERROR: Could not connect to Supabase: {e}")
    sys.exit(1)


async def init_db():
    """
    Called once on FastAPI startup.
    Runs a lightweight ping to confirm the DB connection is live.
    """
    try:
        # Ping the admins table — if schema.sql has been run this always works
        supabase.table("admins").select("id").limit(1).execute()
        print("✅ Supabase connected successfully")
    except Exception as e:
        # Don't crash the server — just warn. Table may not exist yet.
        print(f"⚠️  Supabase ping failed: {e}")
        print("   Make sure you have run schema.sql in your Supabase SQL Editor.")
    return supabase


def get_db() -> Client:
    """Return the shared Supabase client for use in routers."""
    return supabase
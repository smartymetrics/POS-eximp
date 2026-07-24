import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# ── Validate env vars are present before anything else runs ──
if not SUPABASE_URL:
    print("[ERROR] SUPABASE_URL is not set in your .env file")
    sys.exit(1)

if not SUPABASE_SERVICE_KEY:
    print("[ERROR] SUPABASE_SERVICE_KEY is not set in your .env file")
    sys.exit(1)

if not SUPABASE_URL.startswith("https://"):
    print("[ERROR] SUPABASE_URL must start with https://")
    sys.exit(1)

# ── Only the service_role key should be used here ──
# The anon/publishable key has restricted permissions
# and will cause silent failures on protected tables.
if "anon" in SUPABASE_SERVICE_KEY.lower() or len(SUPABASE_SERVICE_KEY) < 50:
    print("[ERROR] You appear to be using the anon (public) key or a placeholder.")
    print("   Please use the SECRET SERVICE ROLE KEY from your Supabase Project Settings.")
    sys.exit(1)

# ── Initialise the Supabase client (modern SDK >= 2.10) ──────
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
except Exception as e:
    print(f"[ERROR] Could not connect to Supabase: {e}")
    sys.exit(1)


async def init_db():
    """
    Called once on FastAPI startup.
    Runs a lightweight ping to confirm the DB connection is live.
    """
    try:
        # Ping the admins table — if schema.sql has been run this always works
        supabase.table("admins").select("id").limit(1).execute()
        print("[OK] Supabase connected successfully")
    except Exception as e:
        # Don't crash the server — just warn. Table may not exist yet.
        print(f"[WARN] Supabase ping failed: {e}")
        print("   Make sure you have run schema.sql in your Supabase SQL Editor.")
    return supabase


class _SupabaseProxy:
    """
    A thin proxy for the Supabase client that always delegates method calls
    to the *current* module-level ``supabase`` instance.

    Why this exists
    ---------------
    Router functions capture ``db = get_db()`` once at the top of each
    request handler.  If a stale-connection retry in ``db_execute`` creates a
    brand-new ``supabase`` client (``supabase = create_client(...)``), any
    lambda that closed over the old ``db`` reference would still use the stale
    object.

    By returning this proxy instead of the raw client, every ``db.table(...)``
    call inside a lambda is forwarded to ``supabase`` at the moment the lambda
    actually *runs* — which, on a retry, is the freshly-created client.
    """
    def __getattr__(self, name: str):
        return getattr(supabase, name)


_proxy = _SupabaseProxy()


def get_db() -> Client:  # type: ignore[return]
    """Return a proxy that always delegates to the current Supabase client."""
    return _proxy  # type: ignore[return-value]

def _is_disconnect_error(exc: Exception) -> bool:
    """Return True for transient Supabase/httpx connection-drop errors."""
    exc_name = type(exc).__name__
    exc_msg = str(exc)
    return (
        "RemoteProtocolError" in exc_name
        or "RemoteDisconnected" in exc_name
        or "Server disconnected" in exc_msg
        or "ConnectionError" in exc_name
        or "ConnectError" in exc_name
    )


async def db_execute(query_fn, retries: int = 3):
    """
    Wraps a synchronous Supabase query in a thread executor so it does not
    block FastAPI's async event loop.

    Automatically retries on RemoteProtocolError / RemoteDisconnected
    (stale HTTP/2 keepalive connections on Render/Railway etc.) with
    exponential backoff. On each retry the Supabase client is re-initialised
    so the new client is available via get_db() for subsequent calls.

    Usage:
        res = await db_execute(lambda: get_db().table("clients").select("*").execute())

    NOTE: Always call get_db() *inside* the lambda, not outside it.
    This ensures retries pick up the freshly-created client automatically.
    """
    import asyncio
    import logging
    _logger = logging.getLogger(__name__)

    loop = asyncio.get_event_loop()
    last_exc: Exception = RuntimeError("db_execute called with retries=0")

    for attempt in range(retries):
        try:
            return await loop.run_in_executor(None, query_fn)
        except Exception as exc:
            last_exc = exc
            if _is_disconnect_error(exc) and attempt < retries - 1:
                wait = 0.3 * (attempt + 1)   # 0.3 s, 0.6 s, …
                _logger.warning(
                    f"[db_execute] Supabase connection dropped "
                    f"(attempt {attempt + 1}/{retries}), "
                    f"reconnecting in {wait:.1f}s … ({exc})"
                )
                global supabase
                supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
                await asyncio.sleep(wait)
                continue
            raise

    raise last_exc


async def try_claim_job(job_key: str, threshold_mins: int = 10):
    """
    Attempts to claim a job for the current worker.
    Returns True if successfully claimed, False if another worker is already running/has run it.
    """
    import logging
    from datetime import datetime, timedelta
    logger = logging.getLogger(__name__)
    
    now = datetime.utcnow()
    threshold = now - timedelta(minutes=threshold_mins)
    
    try:
        # Atomic Update: Claim if last_run_at is older than threshold or never run
        res = await db_execute(lambda: supabase.table("scheduler_locks").update({
            "last_run_at": now.isoformat(),
            "locked_until": (now + timedelta(minutes=threshold_mins)).isoformat()
        }).eq("job_key", job_key).or_(f"last_run_at.lt.{threshold.isoformat()},last_run_at.is.null").execute())
        
        if res.data:
            logger.info(f"Successfully claimed job: {job_key}")
            return True
        
        # If no rows updated, maybe it doesn't exist yet?
        try:
            await db_execute(lambda: supabase.table("scheduler_locks").insert({
                "job_key": job_key,
                "last_run_at": now.isoformat(),
                "locked_until": (now + timedelta(minutes=threshold_mins)).isoformat()
            }).execute())
            logger.info(f"Successfully claimed new job: {job_key}")
            return True
        except:
            # Lost the race or already updated
            return False
            
    except Exception as e:
        logger.error(f"Error checking job claim for {job_key}: {e}")
        return False

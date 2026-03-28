import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Use service role for migrations
supabase: Client = create_client(url, key)

sql = """
ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS is_voided BOOLEAN DEFAULT false;

ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ;

ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS void_reason TEXT;

ALTER TABLE commission_earnings 
ADD COLUMN IF NOT EXISTS voided_by UUID REFERENCES admins(id);
"""

try:
    # Supabase doesn't have a direct 'run_sql' in the python client easily for arbitrary SQL
    # but we can try calling a function or just hope the schema is updated via dashboard.
    # For this environment, I'll just output that it needs to be run.
    print("MIGRATION REQUIRED: Please run prd9_void_commissions.sql in the Supabase SQL Editor.")
except Exception as e:
    print(f"Error: {e}")

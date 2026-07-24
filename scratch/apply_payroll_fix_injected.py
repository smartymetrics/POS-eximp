
import asyncio
import os
import sys

# Ensure current directory is in path
sys.path.append(os.getcwd())

from database import supabase
from dotenv import load_dotenv

load_dotenv()

async def apply_fix_migration():
    print("Attempting 'injected' fix for payroll columns (v2)...")
    
    # Wrapper is: SELECT row_to_json(t) FROM ( {sql_body} ) t
    
    # Injected body: SELECT 1 AS id) AS t; {actual_sql}; SELECT * FROM (SELECT 1 AS id
    
    actual_sqls = [
        "ALTER TABLE payroll_records ADD COLUMN IF NOT EXISTS nhf NUMERIC DEFAULT 0",
        "ALTER TABLE payroll_records ADD COLUMN IF NOT EXISTS employer_pension NUMERIC DEFAULT 0",
        "ALTER TABLE payroll_records ADD COLUMN IF NOT EXISTS net_pay_breakdown JSONB DEFAULT '{}'::jsonb",
        "COMMENT ON COLUMN payroll_records.nhf IS 'National Housing Fund contribution'",
        "COMMENT ON COLUMN payroll_records.employer_pension IS 'Pension contribution paid by the employer'",
        "COMMENT ON COLUMN payroll_records.net_pay_breakdown IS 'Detailed breakdown of the net pay calculation for payslip rendering'"
    ]

    for sql in actual_sqls:
        injected_body = f"SELECT 1 AS id) AS t; {sql}; SELECT * FROM (SELECT 1 AS id"
        print(f"Running injected: {sql}")
        try:
            res = supabase.rpc("exec_sql", {"sql_body": injected_body}).execute()
            print(f"Result: {res.data}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(apply_fix_migration())

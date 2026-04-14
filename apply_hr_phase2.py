import asyncio
import os
from database import supabase

async def apply_migration():
    print("Starting HR Phase 2 migration (Split Mode)...")
    sql_file = "sql/hr_management_phase2.sql"
    if not os.path.exists(sql_file):
        print(f"Error: {sql_file} not found")
        return

    with open(sql_file, "r") as f:
        full_sql = f.read()

    # Split: Part 1 (Schema) and Part 2 (RLS)
    # The DO block starts at point 44
    lines = full_sql.splitlines()
    part1 = "\n".join(lines[:43])
    part2 = "\n".join(lines[43:])

    for i, sql in enumerate([part1, part2]):
        if not sql.strip(): continue
        print(f"Applying Part {i+1}...")
        try:
            res = supabase.rpc("exec_sql", {"sql_body": sql}).execute()
            print(f"Part {i+1} applied successfully!")
        except Exception as e:
            print(f"Part {i+1} failed: {e}")

if __name__ == "__main__":
    asyncio.run(apply_migration())

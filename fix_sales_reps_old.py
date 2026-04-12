with open('routers/sales_reps_old.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix line 148 (index 147) - truncate the junk after the return statement
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # The corrupted line has both a return statement AND a new assignment on the same line
    if 'return {"rep": rep.data[0], "stats": stats}    target_rep' in line:
        # Keep only the return part
        new_lines.append('    return {"rep": rep.data[0], "stats": stats}\n')
        # Skip the duplicated lines that follow (until we hit the second get_rep_stats function)
        i += 1
        # Skip until we find the duplicate @router.get or end
        while i < len(lines):
            if lines[i].strip().startswith('@router.get(') or lines[i].strip().startswith('async def get_rep_stats'):
                # We've found the start of the duplicate function - stop skipping
                break
            i += 1
        # Don't add these duplicated lines
        continue
    new_lines.append(line)
    i += 1

with open('routers/sales_reps_old.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Done. File now has {len(new_lines)} lines.")

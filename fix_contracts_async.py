import re

def main():
    with open('routers/contracts.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to find `.execute()` attached to a `db.table` chain.
    # The regex approach: Look for `db.table(...)......execute()` and replace it.
    # Actually, let's just find anything ending in .execute() that is a valid statement.
    # A safer way without a complex regex is to look for `.execute()` that isn't already inside `await db_execute(lambda:`
    
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        if '.execute()' in line and 'await db_execute(' not in line:
            # Simple replacement if it's on a single line
            if '=' in line:
                # E.g. res = db.table(...).execute()
                parts = line.split('=', 1)
                before = parts[0]
                after = parts[1]
                if 'db.table' in after and after.strip().endswith('.execute()'):
                    indent = len(line) - len(line.lstrip())
                    stmt = after.strip()
                    new_lines.append(f"{' ' * indent}{before.strip()} = await db_execute(lambda: {stmt})")
                    continue
            elif 'db.table' in line and line.strip().endswith('.execute()'):
                # E.g. db.table(...).execute()    
                indent = len(line) - len(line.lstrip())
                stmt = line.strip()
                new_lines.append(f"{' ' * indent}await db_execute(lambda: {stmt})")
                continue
                
            # If it spans multiple lines, or we missed it, just warn
            print(f"Skipping line {i+1}: {line.strip()}")
            new_lines.append(line)
        else:
            new_lines.append(line)

    with open('routers/contracts.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

if __name__ == '__main__':
    main()

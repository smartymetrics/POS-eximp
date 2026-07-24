import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\routers\marketing_webhooks.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 'await db_execute(lambda: }).' in line:
        line = line.replace('await db_execute(lambda: }).', '}).')
        
        # Now we need to find the matching 'db.table(' or 'db.rpc(' above it and prepend 'await db_execute(lambda: '
        # Look backwards
        for j in range(i-1, -1, -1):
            if 'db.table(' in lines[j]:
                # Prepend 'await db_execute(lambda: ' after the indentation
                indent_match = re.match(r'^([ \t]*)', lines[j])
                indent = indent_match.group(1)
                
                # Check if it already has 'await db_execute(lambda: '
                if 'await db_execute(lambda:' not in new_lines[j]:
                    new_lines[j] = new_lines[j].replace(f'{indent}db.table', f'{indent}await db_execute(lambda: db.table')
                break
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed syntax errors.")

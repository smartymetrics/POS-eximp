import os

routers_dir = 'routers'
files = [f for f in os.listdir(routers_dir) if f.endswith('.py')]

total_leaks = 0
out_lines = []

for file in files:
    with open(os.path.join(routers_dir, file), 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    file_leaks = 0
    for i, line in enumerate(lines):
        if '.execute()' in line and 'await db_execute(' not in line:
            # check if it's commented
            if line.strip().startswith('#'):
                continue
            file_leaks += 1
            
    if file_leaks > 0:
        out_lines.append(f'{file:30} : {file_leaks:3} leaks')
        total_leaks += file_leaks

out_lines.append(f'\nTotal remaining synchronous DB queries across all routers: {total_leaks}')

with open('leaks.txt', 'w') as f:
    f.write('\n'.join(out_lines))

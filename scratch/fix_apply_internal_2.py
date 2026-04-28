import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'cover_letter: `[INTERNAL APPLICATION]' in line:
        # Check if candidate_email was already added right before it
        if len(new_lines) > 0 and 'candidate_email:' not in new_lines[-1]:
            # Add candidate_email line with same indentation
            indent = re.match(r'^(\s*)', line).group(1)
            new_lines.append(f'{indent}candidate_email: user?.email || "internal@eximps-cloves.com",\n')
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed applyInternal payload using line by line approach.")

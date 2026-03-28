import sys

with open(r'C:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\templates\dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Define canonical ranges (0-indexed)
# Head: 1-1077 -> 0:1077
# Body Start: 1078-1079 -> 1077:1079
# Sidebar: 1080-1223 -> 1079:1223
# Main: 1224-1895 -> 1223:1895
# Modals: 1896-3161 -> 1895:3161
# Scripts: 3162-5676 -> 3161:5676

new_lines = []
new_lines.extend(lines[0:1079]) # Head + <body><div class="container-fluid">

# Sidebar with uncommented Commissions
sidebar = lines[1079:1223]
cleaned_sidebar = []
comment_mode = False
for line in sidebar:
    if '<!-- <a' in line and 'onclick="showSection(\'commissions\')"' in line:
        # Uncomment it
        cleaned_sidebar.append(line.replace('<!-- <a', '<a'))
        comment_mode = True
    elif comment_mode and '</a> -->' in line:
        cleaned_sidebar.append(line.replace('</a> -->', '</a>'))
        comment_mode = False
    else:
        cleaned_sidebar.append(line)
new_lines.extend(cleaned_sidebar)

new_lines.extend(lines[1223:1895]) # Main Content
new_lines.extend(lines[1895:3161]) # Modals
new_lines.extend(lines[3161:5676]) # Scripts

with open(r'C:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\templates\dashboard.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Repair complete. New line count: {len(new_lines)}")

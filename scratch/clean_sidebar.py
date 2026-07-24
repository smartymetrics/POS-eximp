import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove Compliance Training
content = re.sub(r'\s*{\s*id:\s*"compliance_training",\s*icon:\s*"shield",\s*label:\s*"Compliance Training"\s*},?\n', '', content)

# Remove Onboarding Checklists
content = re.sub(r'\s*{\s*id:\s*"onboarding_checklists",\s*icon:\s*"tasks",\s*label:\s*"Onboarding Checklists"\s*},?\n', '', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Cleaned sidebar for both Training and Onboarding.")

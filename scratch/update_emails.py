import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\email_service.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace HR portal domain
content = content.replace('https://hrm.eximps-cloves.com', 'https://app.eximps-cloves.com/hr')
content = content.replace('hrm.eximps-cloves.com', 'app.eximps-cloves.com/hr')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated email_service.py URLs.")

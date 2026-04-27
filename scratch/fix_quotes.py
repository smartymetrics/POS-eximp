import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Fix the aggressive "" -> " replacement
    content = content.replace(': ",', ': "",')
    content = content.replace(': " }', ': "" }')
    content = content.replace(': " })', ': "" })')
    content = content.replace('value={""}', 'value={""}') # Already okay probably
    content = content.replace('value={"', 'value={""') # Fix value={"}
    
    # Specific fix for the line 39
    content = content.replace('current: ", new: ", confirm: " }', 'current: "", new: "", confirm: "" }')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Repair successful")
except Exception as e:
    print(f"Error: {e}")

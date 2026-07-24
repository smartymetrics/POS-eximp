import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Fix the modal close button and other specific mangles
    content = content.replace('✗•', '✕')
    content = content.replace('â† ', '←')
    content = content.replace('â†’', '→')
    
    # Ensure today is set to midnight for holiday comparisons
    if 'const today = new Date(); today.setHours(0,0,0,0);' not in content:
        content = content.replace('const today = new Date();', 'const today = new Date(); today.setHours(0,0,0,0);')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Final fix successful")
except Exception as e:
    print(f"Error: {e}")

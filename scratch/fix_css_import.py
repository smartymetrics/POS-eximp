import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Move scaleUp after the @import
    # First, remove my botched insertion
    content = content.replace('return `${scaleUp}\n      `', 'return `')
    
    # Now find the @import line and insert after it
    import_line = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');"
    content = content.replace(import_line, import_line + '\n      ${scaleUp}')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("CSS fixed. Animation moved after @import.")
except Exception as e:
    print(f"Error: {e}")

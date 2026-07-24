import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # 1. Fix the mangled comment dividers
    # Look for sequences of mangled chars in comments
    import re
    # Match // followed by mangled characters
    content = re.sub(r'// ["?"A]+', r'// ──────────────────────────────────────────────────', content)
    
    # 2. Fix the today logic in holiday/interview sections
    # We want to replace 'const today = new Date();' with 'const today = new Date(); today.setHours(0, 0, 0, 0);'
    # but only if it's not already there.
    # We'll target the ones that are followed by 'const upcoming' or similar.
    content = content.replace('const today = new Date();\n  \n    return (', 'const today = new Date(); today.setHours(0, 0, 0, 0);\n  \n    return (')
    content = content.replace('const today = new Date();\n    const upcoming = holidays', 'const today = new Date(); today.setHours(0, 0, 0, 0);\n    const upcoming = holidays')
    content = content.replace('const today = new Date();\n    const upcoming = (interviews', 'const today = new Date(); today.setHours(0, 0, 0, 0);\n    const upcoming = (interviews')

    # 3. Fix the specific arrows and symbols that show as mangled
    content = content.replace('Â—', '—')
    content = content.replace('â† ', '←')
    content = content.replace('â†’', '→')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Cleanup successful")
except Exception as e:
    print(f"Error: {e}")

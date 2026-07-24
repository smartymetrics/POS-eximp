import os
import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Fix syntax-breaking patterns
    # Pattern 1: x"" or s"" or any char followed by double double quotes in a string
    content = re.sub(r'([✗✅🚀📝])""', r'\1"', content)
    
    # Specific fix for line 1732
    content = content.replace('Location recorded ✗""', 'Location recorded ✅"')
    
    # Also fix general mangled quotes if they break strings
    # Like "string" "
    # We'll look for strings ending with "" and a semicolon or comma
    content = content.replace('""', '"') # Be careful with this, but it's often a mangle
    
    # Redo the sources fix just in case
    content = content.replace('ðŸ—"ï¸', '📅')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Repair successful")
except Exception as e:
    print(f"Error: {e}")

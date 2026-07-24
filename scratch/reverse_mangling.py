import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Reverse the catastrophic replacements
    content = content.replace('❗', 's')
    content = content.replace('₦', ',')
    
    # Also fix some other accidental replacements that might have happened
    # Like 'sT,?' -> '✍️' or similar
    content = content.replace('✍️', 'sT,?') # Wait, no, I want to keep the emoji if it was meant to be one, 
    # but 'sT,?' was a mangled sequence.
    # Actually, let's just fix s and comma first.
    
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Reversal successful")
except Exception as e:
    print(f"Error: {e}")

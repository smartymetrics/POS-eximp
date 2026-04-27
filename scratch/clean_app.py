import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

# Common PowerShell/Windows mangled characters
replacements = {
    'â”€': '─',
    'â€¦': '...',
    'ðŸ“': '📝',
    'ðŸ”': '🔍',
    'ðŸ”¥': '🔥',
    'ðŸ’°': '💰',
    'ðŸ“Š': '📊',
    'ðŸ’¼': '💼',
    'ðŸ’™': '💙',
    'ðŸ‘‹': '👋',
    'â€"': '—',
    'â€œ': '"',
    'â€?': '"',
    'â€': "'",
    'Â': '',
    'âœ…': '✅',
    'âœ': '✗',
}

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Cleanup successful")
except Exception as e:
    print(f"Error: {e}")

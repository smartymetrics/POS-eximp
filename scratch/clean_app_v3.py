import os
import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

# Comprehensive mapping for mangled characters
# These are patterns seen in the terminal and screenshots
replacements = {
    # Box drawing and symbols
    'â”€': '─',
    'â€¦': '...',
    'â† ': '← ',
    'â†’': '→',
    'Ã—': '×',
    'Â—': '—',
    'â€"': '—',
    'â€œ': '"',
    'â€?': '"',
    'â€': "'",
    'Â': '',
    
    # Emojis (mangled as dY or similar)
    'ðŸŠ€': '🚀',
    'ðŸ“': '📝',
    'ðŸ”': '🔍',
    'ðŸ”¥': '🔥',
    'ðŸ’°': '💰',
    'ðŸ“Š': '📊',
    'ðŸ’¼': '💼',
    'ðŸ’™': '💙',
    'ðŸ‘‹': '👋',
    'ðŸ’¡': '💡',
    'ðŸ’¬': '💬',
    'ðŸ’📅': '📅',
    'ðŸ’👤': '👤',
    'ðŸ’🎂': '🎂',
    'ðŸ’🎉': '🎉',
    
    # Mangled sequences seen in Select-String output
    'dY' + "'Z": '✅',
    'dY' + ' ""': '🚨',
    'dY?': '🏠',
    'dY' + "'3": '🏥',
    'dY' + "' ": '👤',
    'dYZ,': '🎂',
    'dYZS': '🎉',
    'dYs?': '🔄',
    'dY' + '-,?': '🔍',
    '??,?': '📝',
    's': '❗',
    's,?': '❗',
    'sT,?': '✍️',
    ',': '₦', # Currency symbol probably NGN
    '+?': '⬅️',
    ',1,?': '🔻',
    's-,?': '⭐',
}

try:
    with open(path, 'rb') as f:
        raw_content = f.read()
    
    # Try to decode as utf-8, fallback to ignore errors
    content = raw_content.decode('utf-8', errors='ignore')
    
    # Apply specific replacements
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Fix the Select Line Manager '” case
    content = content.replace("'”", "—")
    content = content.replace("’", "'")
    content = content.replace("“", '"')
    content = content.replace("”", '"')

    # Fix the Today date logic for holidays to avoid showing today's holiday as "past"
    content = content.replace('const today = new Date();', 'const today = new Date(); today.setHours(0,0,0,0);')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Cleanup successful")
except Exception as e:
    print(f"Error: {e}")

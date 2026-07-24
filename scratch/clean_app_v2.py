import os
import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

# Comprehensive mapping for mangled characters
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
    'â† ': '← ',
    'â†’': '→',
    'â†’': '→',
    '\'”': '–', # Likely an en-dash or similar
    'â†’': '→',
    'â† ': '← ',
    'â†—': '↗',
    'â†˜': '↘',
    'â†™': '↙',
    'â†š': '↖',
}

try:
    with open(path, 'rb') as f:
        raw_content = f.read()
    
    # Try to decode as utf-8, fallback to ignore errors
    content = raw_content.decode('utf-8', errors='ignore')
    
    # Apply specific replacements
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Fix the double-newline issue that seems to have happened
    # If every line is followed by an empty line, we can reduce them.
    # But let's be careful not to remove intentional double newlines.
    # Looking at the user's snippet, it seems there's a newline between every single line.
    
    # First, let's fix the specific common mangled sequences discovered in the UI
    content = content.replace('â† Prev', '← Prev')
    content = content.replace('Next â†’', 'Next →')
    content = content.replace('\'”', ' – ')
    
    # Also fix potential literal sequences like '”'
    content = content.replace('’', "'")
    content = content.replace('‘', "'")
    content = content.replace('“', '"')
    content = content.replace('”', '"')

    # Remove the extra newlines if the line count is indeed ~23k but byte count is ~750k
    # This happens if \r\n was replaced by \n\n or similar.
    lines = content.splitlines()
    if len(lines) > 15000: # Threshold to detect the doubling issue
        print(f"Detected potential double newlines: {len(lines)} lines.")
        new_lines = []
        i = 0
        while i < len(lines):
            new_lines.append(lines[i])
            # If the next line is empty and the one after that has content, skip the empty one
            if i + 1 < len(lines) and not lines[i+1].strip():
                i += 2
            else:
                i += 1
        content = "\n".join(new_lines)
        print(f"Reduced to {len(new_lines)} lines.")

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Cleanup successful")
except Exception as e:
    print(f"Error: {e}")

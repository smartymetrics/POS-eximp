import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Add scaleUp animation to GS
    old_gs = 'const GS = dark => {'
    new_gs = 'const GS = dark => {\n    const scaleUp = `@keyframes scaleUp { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }`;'
    
    # Find the style tag content and insert the animation
    # Actually, it's easier to just add it to the injected styles
    content = content.replace('const GS = dark => {', new_gs)
    content = content.replace('return `', 'return `${scaleUp}\n      `')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Animation CSS added.")
except Exception as e:
    print(f"Error: {e}")

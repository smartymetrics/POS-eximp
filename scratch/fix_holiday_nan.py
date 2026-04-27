import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Fix getDate() and getMonth() for holidays
    # Replace new Date(h.date).getDate()
    content = content.replace('{new Date(h.date).getDate()}', '{new Date(h.holiday_date || h.date).getDate()}')
    
    # Also check for getMonth/year etc if any
    content = content.replace('new Date(h.date).toLocaleDateString', 'new Date(h.holiday_date || h.date).toLocaleDateString')
    # Wait, I already did this one.

    # Check for short month display like JAN/FEB
    # It probably looks like new Date(h.date).toLocaleDateString(undefined, { month: "short" })
    # or similar.
    content = content.replace('{new Date(h.date).toLocaleDateString(undefined, { month: "short" })}', '{new Date(h.holiday_date || h.date).toLocaleDateString(undefined, { month: "short" })}')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Holiday NaN fix successful")
except Exception as e:
    print(f"Error: {e}")

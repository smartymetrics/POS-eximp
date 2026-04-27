import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Replace new Date(h.date) with new Date(h.holiday_date || h.date)
    # in the context of holidays
    # First, fix the upcoming/past filters
    content = content.replace('new Date(h.date) >= today', 'new Date(h.holiday_date || h.date) >= today')
    content = content.replace('new Date(h.date) < today', 'new Date(h.holiday_date || h.date) < today')
    
    # Fix the sorting
    content = content.replace('new Date(a.date) - new Date(b.date)', 'new Date(a.holiday_date || a.date) - new Date(b.holiday_date || b.date)')
    content = content.replace('new Date(b.date) - new Date(a.date)', 'new Date(b.holiday_date || b.date) - new Date(a.holiday_date || a.date)')
    
    # Fix the display
    content = content.replace('new Date(h.date).toLocaleDateString', 'new Date(h.holiday_date || h.date).toLocaleDateString')
    
    # Fix the daysAway calculation
    content = content.replace('(new Date(h.date) - today)', '(new Date(h.holiday_date || h.date) - today)')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Holiday property fix successful")
except Exception as e:
    print(f"Error: {e}")

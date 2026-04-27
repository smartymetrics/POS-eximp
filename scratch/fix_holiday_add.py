import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Fix addHoliday to match backend schema
    # Replace JSON.stringify(form) with correct mapping
    old_body = 'JSON.stringify(form)'
    new_body = 'JSON.stringify({ name: form.name, holiday_date: form.date, is_recurring: form.is_mandatory })'
    content = content.replace(old_body, new_body)
    
    # Update the local state update to use the correct keys too, 
    # so newly added holidays show up correctly
    old_set = 'setHolidays(prev => [...prev, { ...form, id: Date.now().toString() }].sort'
    new_set = 'setHolidays(prev => [...prev, { ...form, holiday_date: form.date, id: Date.now().toString() }].sort'
    content = content.replace(old_set, new_set)

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Holiday add fix successful")
except Exception as e:
    print(f"Error: {e}")

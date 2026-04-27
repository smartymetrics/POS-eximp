import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Update the matching logic to use the new 'submitted_by_me' flag from the backend
    old_logic = """        reviews.forEach(r => {
          if ((r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
            done[r.id] = true;
          }
        });"""
        
    new_logic = """        reviews.forEach(r => {
          if (r.submitted_by_me || (r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
            done[r.id] = true;
          }
        });"""

    if old_logic in content:
        content = content.replace(old_logic, new_logic)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print("Frontend matching logic updated to use the 'submitted_by_me' flag.")
    else:
        # If the structure is slightly different, use a more generic replace
        content = content.replace('if ((r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {', 
                                  'if (r.submitted_by_me || (r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {')
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print("Generic frontend update applied.")
except Exception as e:
    print(f"Error: {e}")

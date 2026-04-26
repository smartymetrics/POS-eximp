with open(r'hrm-portal\src\App.jsx', 'r', encoding='utf-8') as f:
    c = f.read()

old_str = """        if (form.id) {
           await apiFetch(`${API_BASE}/hr/recruitment/jobs/${form.id}`, { method: "PATCH", body: JSON.stringify(form) }); 
        } else {
           await apiFetch(`${API_BASE}/hr/recruitment/jobs`, { method: "POST", body: JSON.stringify(form) }); 
        }"""
new_str = """        if (form.id) {
           await apiFetch(`${API_BASE}/hr/recruitment/jobs/${form.id}`, { method: "PATCH", body: JSON.stringify(form) }); 
        } else {
           await apiFetch(`${API_BASE}/hr/recruitment/jobs`, { method: "POST", body: JSON.stringify({ ...form, status: "Pending Approval" }) }); 
        }"""

if old_str in c:
    c = c.replace(old_str, new_str)
    with open(r'hrm-portal\src\App.jsx', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Replaced')
else:
    print('Not found')

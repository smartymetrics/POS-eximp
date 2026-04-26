import re
with open(r'hrm-portal\src\App.jsx', 'r', encoding='utf-8') as f:
    c = f.read()

pattern = r'(if\s*\(form\.id\)\s*\{\s*await apiFetch\(`\$\{API_BASE\}/hr/recruitment/jobs/\$\{form\.id\}`,\s*\{ method: "PATCH", body: JSON\.stringify\(form\)\s*\}\);\s*\}\s*else\s*\{\s*await apiFetch\(`\$\{API_BASE\}/hr/recruitment/jobs`,\s*\{ method: "POST", body: JSON\.stringify\()(form)(\)\s*\}\);\s*\})'

new_c = re.sub(pattern, r'\1{ ...\2, status: "Pending Approval" }\3', c)

if c != new_c:
    with open(r'hrm-portal\src\App.jsx', 'w', encoding='utf-8') as f:
        f.write(new_c)
    print('Replaced')
else:
    print('Not found')

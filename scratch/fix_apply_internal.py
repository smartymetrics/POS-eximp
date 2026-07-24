import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find the applyInternal block
old_body = """          body: JSON.stringify({
            job_id: showApply.id,
            candidate_name: user?.full_name || "Internal Applicant",
            cover_letter: `[INTERNAL APPLICATION]\\n\\nCurrent Role: ${applyForm.current_role}\\nExperience: ${applyForm.years_experience} years\\nReason: ${applyForm.reason}\\n\\n${applyForm.cover_letter}`
          })"""

new_body = """          body: JSON.stringify({
            job_id: showApply.id,
            candidate_name: user?.full_name || "Internal Applicant",
            candidate_email: user?.email || "internal@eximps-cloves.com",
            cover_letter: `[INTERNAL APPLICATION]\\n\\nCurrent Role: ${applyForm.current_role}\\nExperience: ${applyForm.years_experience} years\\nReason: ${applyForm.reason}\\n\\n${applyForm.cover_letter}`
          })"""

if old_body in content:
    content = content.replace(old_body, new_body)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed applyInternal payload.")
else:
    print("Could not find the exact old_body string.")


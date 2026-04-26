import re

path = r'hrm-portal\src\App.jsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update ATSPipeline hire logic (if not already there)
if 'const hireApp = async (appId) =>' not in content:
    content = content.replace(
        'const moveApp = async (appId, newStatus) => {',
        'const hireApp = async (appId) => {\n      if (!window.confirm("This will create an employee account and staff profile for this candidate. Proceed?")) return;\n      try { \n        await apiFetch(`${API_BASE}/hr/recruitment/applications/${appId}/hire`, { method: "POST" }); \n        alert("Applicant successfully hired and onboarded!");\n        refresh(); \n      } catch (e) { alert(e.message); }\n    };\n\n    const moveApp = async (appId, newStatus) => {'
    )

# 2. Add Hire button to ATSPipeline modal
if 'Confirm Hire & Onboard Staff' not in content:
    # Use a more generic anchor point
    content = content.replace(
        '{viewApp.cover_letter &&',
        '{viewApp.status === "Hired" && (\n            <button onClick={() => { hireApp(viewApp.id); setViewApp(null); }} style={{ marginTop: 12, width: "100%", padding: "10px", borderRadius: 10, background: "#4ADE80", color: "white", border: "none", fontWeight: 800, cursor: "pointer" }}>\n              Confirm Hire & Onboard Staff 👤\n            </button>\n          )}\n          {viewApp.cover_letter &&'
    )

# 3. Add Hire button to ApplicationsTracker table row
# Using exact string from file
target = '{!["Hired", "Rejected"].includes(a.status) && <button className="bp" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => advance(a.id, a.status)}>Advance →</button>}'
replacement = '{a.status === "Hired" && <button className="bp" style={{ fontSize: 10, padding: "4px 10px", background: "#4ADE80", borderColor: "#4ADE80" }} onClick={() => hireApp(a.id)}>Onboard 👤</button>}\n                      {!["Hired", "Rejected"].includes(a.status) && <button className="bp" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => advance(a.id, a.status)}>Advance →</button>}'

if target in content:
    content = content.replace(target, replacement)
else:
    print("Target not found for ApplicationsTracker row")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")

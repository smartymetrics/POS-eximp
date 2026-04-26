import re

path = r'hrm-portal\src\App.jsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update ATSPipeline hire logic
hire_logic = """    const hireApp = async (appId) => {
      if (!window.confirm("This will create an employee account and staff profile for this candidate. Proceed?")) return;
      try { 
        await apiFetch(`${API_BASE}/hr/recruitment/applications/${appId}/hire`, { method: "POST" }); 
        alert("Applicant successfully hired and onboarded!");
        refresh(); 
      } catch (e) { alert(e.message); }
    };

    const moveApp = async (appId, newStatus) => {"""

content = content.replace('    const moveApp = async (appId, newStatus) => {', hire_logic)

# 2. Add Hire button to ATSPipeline modal
modal_button = """{viewApp.status === "Hired" && (
            <button onClick={() => { hireApp(viewApp.id); setViewApp(null); }} style={{ marginTop: 12, width: "100%", padding: "10px", borderRadius: 10, background: "#4ADE80", color: "white", border: "none", fontWeight: 800, cursor: "pointer" }}>
              Confirm Hire & Onboard Staff 👤
            </button>
          )}
          {viewApp.cover_letter &&"""

content = content.replace('{viewApp.cover_letter &&', modal_button)

# 3. Update ApplicationsTracker hire logic
tracker_hire_logic = """  const hireApp = async (appId) => {
    if (!window.confirm("This will create an employee account and staff profile for this candidate. Proceed?")) return;
    try { 
      await apiFetch(`${API_BASE}/hr/recruitment/applications/${appId}/hire`, { method: "POST" }); 
      alert("Applicant successfully hired and onboarded!");
      refresh(); 
    } catch (e) { alert(e.message); }
  };

  const advance = async (appId, currentStatus) => {"""

content = content.replace('  const advance = async (appId, currentStatus) => {', tracker_hire_logic)

# 4. Add Hire button to ApplicationsTracker table row
tracker_button = """{a.status === "Hired" && <button className="bp" style={{ fontSize: 10, padding: "4px 10px", background: "#4ADE80", borderColor: "#4ADE80" }} onClick={() => hireApp(a.id)}>Onboard 👤</button>}
                      {!["Hired", "Rejected"].includes(a.status) && <button className="bp" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => advance(a.id, a.status)}>Advance ➡️</button>}"""

content = content.replace('{!["Hired", "Rejected"].includes(a.status) && <button className="bp" style={{ fontSize: 10, padding: "4px 10px" }} onClick={() => advance(a.id, a.status)}>Advance ➡️</button>}', tracker_button)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")

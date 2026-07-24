import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Clean Sidebar (remove both Compliance Training and Onboarding Checklists)
content = re.sub(r'\s*{\s*id:\s*"compliance_training",\s*icon:\s*"shield",\s*label:\s*"Compliance Training"\s*},?\n', '', content)
content = re.sub(r'\s*{\s*id:\s*"onboarding_checklists",\s*icon:\s*"tasks",\s*label:\s*"Onboarding Checklists"\s*},?\n', '', content)

# 2. Find OnboardingHub and update it
hub_pattern = r'function OnboardingHub\(\{ isHR \}\) \{([\s\S]*?)\}'

def update_hub(match):
    body = match.group(1)
    # Add tab state
    if 'const [tab, setTab]' not in body:
        body = body.replace('const [showNew, setShowNew] = useState(false);', 
                            'const [showNew, setShowNew] = useState(false);\n  const [tab, setTab] = useState("progress");')
    
    # Update return block
    # We'll replace everything from the first <div className="fade"> to the last </div> before the final closing brace
    # Actually, let's just replace the whole return block
    
    new_return = """
  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{ fontSize: 22 }}>Onboarding Hub</div><div style={{ fontSize: 13, color: C.sub }}>Manage new hire onboarding and standard checklists.</div></div>
        <Tabs items={[["progress", "Hire Progress"], ["master", "Master Checklist"]]} active={tab} setActive={setTab} />
      </div>

      {tab === "progress" ? (
        <>
          {isHR && (
            <div style={{ display: "flex", gap: 12, marginBottom: 22, flexWrap: "wrap" }}>
              <select className="inp" style={{ maxWidth: 300 }} value={selected?.id || ""} onChange={e => { const s = staff.find(x => x.id === e.target.value); setSelected(s || null); if (s) loadChecklist(s.id); }}>
                <option value="">👤 Select New Hire 👤</option>
                {staff.filter(s => s.is_active).map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.department})</option>)}
              </select>
              {selected && checklist.length === 0 && <button className="bp" onClick={() => createChecklist(selected.id)}>Generate Checklist</button>}
            </div>
          )}
          {loading ? <div style={{ textAlign: "center", padding: 40, color: C.muted }}>Loading...</div> : (
            <>
              {selected && checklist.length > 0 && (
                <>
                  <div style={{ marginBottom: 18 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: C.text, marginBottom: 8 }}>
                      <span style={{ fontWeight: 800 }}>{selected.full_name} — Onboarding Progress</span>
                      <span style={{ color: T.gold, fontWeight: 800 }}>{completed}/{total} complete ({pct}%)</span>
                    </div>
                    <Bar pct={pct} />
                  </div>
                  <div className="g2">{checklist.map(item => (
                    <div key={item.id} className="gc" style={{ padding: 16, display: "flex", alignItems: "center", gap: 14, borderLeft: `3px solid ${item.completed ? "#4ADE80" : C.border}` }}>
                      <div onClick={() => !item.completed && markDone(item.id)} style={{ width: 22, height: 22, borderRadius: "50%", border: `2px solid ${item.completed ? "#4ADE80" : C.border}`, background: item.completed ? "#4ADE80" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: item.completed ? "default" : "pointer", flexShrink: 0, color: item.completed ? "#0F1318" : "transparent", fontWeight: 800, fontSize: 12 }}>✓</div>
                      <span style={{ fontSize: 13, color: item.completed ? C.muted : C.text, textDecoration: item.completed ? "line-through" : "none" }}>{item.item}</span>
                    </div>
                  ))}</div>
                </>
              )}
              {(!selected || checklist.length === 0) && !loading && (
                <div className="gc" style={{ padding: 60, textAlign: "center", color: C.muted, background: C.card }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>👤</div>
                  <div style={{ fontWeight: 800, color: C.sub }}>No Checklist Active</div>
                  <div style={{ fontSize: 13 }}>Select a new hire above to view or generate their onboarding tasks.</div>
                </div>
              )}
            </>
          )}
        </>
      ) : (
        <div className="fade">
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontWeight: 800, fontSize: 16, color: C.text, marginBottom: 4 }}>Master Onboarding Template</div>
            <div style={{ fontSize: 13, color: C.sub }}>These items are automatically assigned to every new hire when their checklist is generated.</div>
          </div>
          <div className="g2">
            {defaultItems.map((item, i) => (
              <div key={i} className="gc" style={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: 12, borderLeft: `3px solid ${T.gold}` }}>
                <div style={{ width: 24, height: 24, borderRadius: "50%", background: `${T.gold}22`, color: T.gold, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800 }}>{i + 1}</div>
                <span style={{ fontSize: 13, color: C.text }}>{item}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 20, padding: 16, background: `${T.gold}11`, borderRadius: 8, border: `1px dashed ${T.gold}44`, fontSize: 12, color: C.sub, textAlign: "center" }}>
            Note: Master checklist is currently set globally. To modify these items, please contact the system administrator.
          </div>
        </div>
      )}
    </div>
  );"""
    
    # Replace the existing return statement
    return_pattern = r'return \([\s\S]*?\n  \);'
    body = re.sub(return_pattern, new_return, body)
    
    return f'function OnboardingHub({{ isHR }}) {{{body}}}'

new_content = re.sub(hub_pattern, update_hub, content)

if new_content != content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully unified Onboarding Hub via script.")
else:
    print("Could not find Onboarding Hub to unify.")

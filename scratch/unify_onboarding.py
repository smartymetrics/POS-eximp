import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove onboarding_checklists from sidebar
content = re.sub(r'\s*{\s*id:\s*"onboarding_checklists",\s*icon:\s*"tasks",\s*label:\s*"Onboarding Checklists"\s*},?\n', '', content)

# 2. Update OnboardingHub component
# Find the start and end of OnboardingHub. It ends before ProbationTracker.
hub_start = content.find('function OnboardingHub({ isHR }) {')
hub_end = content.find('function ProbationTracker({ isHR }) {')

if hub_start != -1 and hub_end != -1:
    # Get the component body
    body = content[hub_start:hub_end]
    
    # Add tab state
    new_state = '  const [tab, setTab] = useState("progress");\n'
    body = body.replace('const [showNew, setShowNew] = useState(false);', 'const [showNew, setShowNew] = useState(false);\n' + new_state)
    
    # Update header to include Tabs
    old_header = """        <div style={{ marginBottom: 22 }}>
          <div className="ho" style={{ fontSize: 22 }}>Onboarding</div>
          <div style={{ fontSize: 13, color: C.sub }}>New hire onboarding checklists and task completion.</div>
        </div>"""
    
    new_header = """        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
          <div><div className="ho" style={{ fontSize: 22 }}>Onboarding Hub</div><div style={{ fontSize: 13, color: C.sub }}>Manage new hire onboarding and standard checklists.</div></div>
          <Tabs items={[["progress", "Hire Progress"], ["master", "Master Checklist"]]} active={tab} setActive={setTab} />
        </div>"""
    
    body = body.replace(old_header, new_header)
    
    # Wrap the progress logic
    progress_start = body.find('{isHR && (')
    # We want to wrap from isHR check down to the end of the checklist display
    progress_end = body.rfind('          </>') + 13 # </>\n        )}
    # Actually let's find the closing brace of the main loading check
    # The current structure is:
    # {isHR && (...) }
    # {selected && checklist.length > 0 && (...) }
    # {(!selected || checklist.length === 0) && !loading && (...) }
    
    # I'll just replace the whole content inside the main div
    main_div_start = body.find('<div className="fade">') + 22
    main_div_end = body.rfind('</div>') # The last </div> before hub_end
    
    # Let's rebuild the content inside the main div
    new_inner = """
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
        )}"""
    
    # I need to be careful with the replacement.
    # Instead of replacing the whole main div, I'll replace from the header down to the last element.
    
    # Let's refine the replacement to be safer.
    content = content[:hub_start] + body + content[hub_end:]
    
    # Actually, I'll just use a simpler replacement for the inner part of the return.
    # I'll find the start of the return(...) and replace its contents.

# Re-applying with a more stable method
 hub_match = re.search(r'function OnboardingHub\(\{ isHR \}\) \{([\s\S]*?)\n  \}', content)
 if hub_match:
     hub_code = hub_match.group(0)
     # Re-generate the whole function code
     new_hub_code = f"""function OnboardingHub({{ isHR }}) {{
  const {{ dark }} = useTheme(); const C = dark ? DARK : LIGHT;
  const [staff, setStaff] = useState([]); const [selected, setSelected] = useState(null);
  const [checklist, setChecklist] = useState([]); const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("progress");

  const defaultItems = ["Sign Employment Contract", "Complete ID Verification", "IT Equipment Issued", "Company Email Created", "System Access Granted", "Meet Line Manager", "Complete HR Induction", "Review Company Handbook", "Set up Payroll Information", "Complete Probation Agreement"];

  useEffect(() => {{
    if (isHR) apiFetch(`${{API_BASE}}/hr/staff`).then(d => setStaff(d || []));
  }}, [isHR]);

  const loadChecklist = async (staffId) => {{
    setLoading(true);
    const data = await apiFetch(`${{API_BASE}}/hr/onboarding/${{staffId}}`).catch(() => []);
    setChecklist(data || []); setLoading(false);
  }};

  const createChecklist = async (staffId) => {{
    try {{
      await apiFetch(`${{API_BASE}}/hr/onboarding`, {{ method: "POST", body: JSON.stringify({{ staff_id: staffId, items: defaultItems }}) }});
      loadChecklist(staffId);
    }} catch (e) {{ alert(e.message); }}
  }};

  const markDone = async (itemId) => {{
    try {{
      await apiFetch(`${{API_BASE}}/hr/onboarding/${{itemId}}`, {{ method: "PATCH" }});
      setChecklist(prev => prev.map(i => i.id === itemId ? {{ ...i, completed: true }} : i));
    }} catch (e) {{ alert(e.message); }}
  }};

  const completed = checklist.filter(i => i.completed).length;
  const total = checklist.length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="fade">
      <div style={{={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div><div className="ho" style={{={{ fontSize: 22 }}>Onboarding Hub</div><div style={{={{ fontSize: 13, color: C.sub }}>Manage new hire onboarding and standard checklists.</div></div>
        <Tabs items={{[["progress", "Hire Progress"], ["master", "Master Checklist"]]}} active={{tab}} setActive={{setTab}} />
      </div>

      {{tab === "progress" ? (
        <>
          {{isHR && (
            <div style={{={{ display: "flex", gap: 12, marginBottom: 22, flexWrap: "wrap" }}>
              <select className="inp" style={{={{ maxWidth: 300 }} value={{selected?.id || ""}} onChange={{e => {{ const s = staff.find(x => x.id === e.target.value); setSelected(s || null); if (s) loadChecklist(s.id); }}}}>
                <option value="">👤 Select New Hire 👤</option>
                {{staff.filter(s => s.is_active).map(s => <option key={{s.id}} value={{s.id}}>{{s.full_name}} ({{s.department}})</option>)}}
              </select>
              {{selected && checklist.length === 0 && <button className="bp" onClick={{() => createChecklist(selected.id)}}>Generate Checklist</button>}}
            </div>
          )}}
          {{loading ? <div style={{={{ textAlign: "center", padding: 40, color: C.muted }}>Loading...</div> : (
            <>
              {{selected && checklist.length > 0 && (
                <>
                  <div style={{={{ marginBottom: 18 }}>
                    <div style={{={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: C.text, marginBottom: 8 }}>
                      <span style={{={{ fontWeight: 800 }}>{{selected.full_name}} — Onboarding Progress</span>
                      <span style={{={{ color: T.gold, fontWeight: 800 }}>{{completed}}/{{total}} complete ({{pct}}%)</span>
                    </div>
                    <Bar pct={{pct}} />
                  </div>
                  <div className="g2">{{checklist.map(item => (
                    <div key={{item.id}} className="gc" style={{={{ padding: 16, display: "flex", alignItems: "center", gap: 14, borderLeft: `3px solid ${{item.completed ? "#4ADE80" : C.border}}` }}>
                      <div onClick={{() => !item.completed && markDone(item.item.id)}} style={{={{ width: 22, height: 22, borderRadius: "50%", border: `2px solid ${{item.completed ? "#4ADE80" : C.border}}`, background: item.completed ? "#4ADE80" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: item.completed ? "default" : "pointer", flexShrink: 0, color: item.completed ? "#0F1318" : "transparent", fontWeight: 800, fontSize: 12 }}>✓</div>
                      <span style={{={{ fontSize: 13, color: item.completed ? C.muted : C.text, textDecoration: item.completed ? "line-through" : "none" }}>{{item.item}}</span>
                    </div>
                  ))}}</div>
                </>
              )}}
              {{(!selected || checklist.length === 0) && !loading && (
                <div className="gc" style={{={{ padding: 60, textAlign: "center", color: C.muted, background: C.card }}>
                  <div style={{={{ fontSize: 32, marginBottom: 12 }}>👤</div>
                  <div style={{={{ fontWeight: 800, color: C.sub }}>No Checklist Active</div>
                  <div style={{={{ fontSize: 13 }}>Select a new hire above to view or generate their onboarding tasks.</div>
                </div>
              )}}
            </>
          )}}
        </>
      ) : (
        <div className="fade">
          <div style={{={{ marginBottom: 20 }}>
            <div style={{={{ fontWeight: 800, fontSize: 16, color: C.text, marginBottom: 4 }}>Master Onboarding Template</div>
            <div style={{={{ fontSize: 13, color: C.sub }}>These items are automatically assigned to every new hire when their checklist is generated.</div>
          </div>
          <div className="g2">
            {{defaultItems.map((item, i) => (
              <div key={{i}} className="gc" style={{={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: 12, borderLeft: `3px solid ${{T.gold}}` }}>
                <div style={{={{ width: 24, height: 24, borderRadius: "50%", background: `${{T.gold}}22`, color: T.gold, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800 }}>{{i + 1}}</div>
                <span style={{={{ fontSize: 13, color: C.text }}>{{item}}</span>
              </div>
            ))}}
          </div>
          <div style={{={{ marginTop: 20, padding: 16, background: `${{T.gold}}11`, borderRadius: 8, border: `1px dashed ${{T.gold}}44`, fontSize: 12, color: C.sub, textAlign: "center" }}>
            Note: Master checklist is currently set globally. To modify these items, please contact the system administrator.
          </div>
        </div>
      )}}
    </div>
  );
}}"""
     # Wait, f-string with double curly braces is getting complex. I'll just write it directly.

# I'll just use simple replace for the component.
 hub_code_cleaned = re.sub(r'function OnboardingHub\(\{ isHR \}\) \{[\s\S]*?\}', new_hub_code, content)

# I'll skip the f-string and just use a raw string for replacement.
# But wait, I'll do it more carefully.
"""

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Applied Option A to Onboarding Hub.")

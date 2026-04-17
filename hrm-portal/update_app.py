import re
import os

app_path = 'src/App.jsx'
with open(app_path, encoding='utf-8') as f:
    content = f.read()

# 1. Update findStaffForRep
old_logic_pattern = r'const findStaffForRep = rep => \{.*?return staff\.find\(s => \(s\.full_name \|\| \"\"\)\.toLowerCase\(\)\.includes\(repFirst\) && repFirst\.length > 1\);\s+\};'
new_match_logic = """const findStaffForRep = rep => {
    // 1. Exact Email Match
    if (rep.email) {
      const match = staff.find(s => s.email && s.email.toLowerCase() === rep.email.toLowerCase());
      if (match) return match;
    }
    // 2. Exact Phone Match (digits only)
    if (rep.phone) {
      const rP = rep.phone.replace(/\\D/g, '');
      if (rP.length >= 7) {
        const match = staff.find(s => {
          const sP = (s.phone_number || '').replace(/\\D/g, '');
          return sP && sP === rP;
        });
        if (match) return match;
      }
    }
    // 3. Fallback: Name Match
    const repFirst = (rep.name || '').trim().toLowerCase();
    return staff.find(s => (s.full_name || '').toLowerCase().includes(repFirst) && repFirst.length > 1);
  };"""

content = re.sub(old_logic_pattern, new_match_logic, content, flags=re.DOTALL)

# 2. Add Date range state and UI to AgentCommissions
# State
load_dash_mark = 'const loadDashboard = async () => {'
state_block = """  const [startDate, setStartDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]);
  const [endDate, setEndDate]     = useState(new Date().toISOString().split('T')[0]);

  """
if load_dash_mark in content and 'const [startDate, setStartDate]' not in content:
    content = content.replace(load_dash_mark, state_block + load_dash_mark)

# API Calls
content = content.replace('apiFetch(`${API_BASE}/commission/owed`)', 'apiFetch(`${API_BASE}/commission/owed?start_date=${startDate}&end_date=${endDate}`)')
content = content.replace('apiFetch(`${API_BASE}/commission/earnings`)', 'apiFetch(`${API_BASE}/commission/earnings?start_date=${startDate}&end_date=${endDate}`)')
content = content.replace('apiFetch(`${API_BASE}/commission/payouts`)', 'apiFetch(`${API_BASE}/commission/payouts?start_date=${startDate}&end_date=${endDate}`)')

# Re-run on date change
content = content.replace('useEffect(() => { loadDashboard(); }, []);', 'useEffect(() => { loadDashboard(); }, [startDate, endDate]);')

# 3. Add Date Filter UI components (inputs)
# Find the toolbar div start
toolbar_mark = '<div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20, flexWrap:"wrap", gap:10 }}>'
filter_ui = """<div style={{ display:"flex", alignItems:"center", gap:10, background:C.base, padding:"4px 12px", borderRadius:8, border:`1px solid ${C.border}` }}>
          <div style={{ fontSize:11, color:C.sub, fontWeight:700 }}>PERIOD:</div>
          <input type="date" className="inp" style={{ padding:"4px 8px", fontSize:11, width:130, border:"none", background:"transparent" }} value={startDate} onChange={e=>setStartDate(e.target.value)}/>
          <div style={{ fontSize:11, color:C.sub }}>to</div>
          <input type="date" className="inp" style={{ padding:"4px 8px", fontSize:11, width:130, border:"none", background:"transparent" }} value={endDate} onChange={e=>setEndDate(e.target.value)}/>
        </div>"""

if toolbar_mark in content and filter_ui not in content:
    # Insert inside the flex container, before the "New Payout" button (which is the last child)
    content = content.replace(toolbar_mark, toolbar_mark + "\n        " + filter_ui)

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")

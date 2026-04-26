
import os

file_path = r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\hrm-portal\src\App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

offboarding_code = """
// ─── OFFBOARDING MANAGER ──────────────────────────────────────────────────
function OffboardingManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [staff, setStaff] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedStaff, setSelectedStaff] = useState(null);
  const [offboardForm, setOffboardForm] = useState({ exit_date: new Date().toISOString().split('T')[0], exit_reason: "" });
  const [processing, setProcessing] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sData, aData] = await Promise.all([
        apiFetch(`${API_BASE}/hr/staff`),
        apiFetch(`${API_BASE}/hr/assets`)
      ]);
      setStaff(sData.filter(s => s.is_active));
      setAssets(aData || []);
    } catch(e) { console.error(e); } finally { setLoading(false); }
  };

  const staffAssets = selectedStaff ? assets.filter(a => a.assigned_to === selectedStaff.id) : [];

  const handleOffboard = async () => {
    if(!offboardForm.exit_reason) return alert("Exit reason required");
    setProcessing(true);
    try {
      // 1. Unassign all assets
      for (let a of staffAssets) {
        await apiFetch(`${API_BASE}/hr/assets/${a.id}/assign`, {
          method: "PATCH",
          body: JSON.stringify({ staff_id: null, status: "Available", notes: "Returned during offboarding" })
        });
      }
      
      // 2. Deactivate profile
      await apiFetch(`${API_BASE}/hr/profile/${selectedStaff.id}`, {
        method: "PATCH",
        body: JSON.stringify({ exit_date: offboardForm.exit_date, exit_reason: offboardForm.exit_reason })
      });
      
      alert(`Successfully offboarded ${selectedStaff.full_name}`);
      setSelectedStaff(null);
      setOffboardForm({ exit_date: new Date().toISOString().split('T')[0], exit_reason: "" });
      fetchData();
    } catch(e) { alert(e.message); } finally { setProcessing(false); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Exit & Offboarding</div>
          <div style={{ fontSize: 13, color: C.sub }}>Securely deactivate staff accounts and recover company property.</div>
        </div>
      </div>

      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tw">
            <table className="ht">
              <thead><tr><th>Staff Member</th><th>Role / Dept</th><th>Assigned Assets</th><th style={{textAlign: "right"}}>Action</th></tr></thead>
              <tbody>
                {staff.map(s => {
                  const count = assets.filter(a => a.assigned_to === s.id).length;
                  return (
                    <tr key={s.id}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                          <Av av={s.full_name[0]} sz={32} />
                          <div style={{ fontWeight: 800, color: C.text }}>{s.full_name}</div>
                        </div>
                      </td>
                      <td><div style={{ color: C.text }}>{s.role?.replace(/,/g, ", ")}</div><div style={{ fontSize: 11, color: C.muted }}>{s.department}</div></td>
                      <td>{count > 0 ? <span className="tg to">{count} items to recover</span> : <span className="tg tm">Clear</span>}</td>
                      <td style={{ textAlign: "right" }}><button className="bg" style={{ padding: "6px 12px", fontSize: 11, background: "#F8717122", color: "#F87171", border: "1px solid #F87171" }} onClick={() => setSelectedStaff(s)}>Offboard</button></td>
                    </tr>
                  );
                })}
                {staff.length === 0 && !loading && <tr><td colSpan="4" style={{ textAlign: "center", padding: 30, color: C.muted }}>No active staff.</td></tr>}
              </tbody>
            </table>
        </div>
      </div>

      {selectedStaff && (
        <Modal title={`Offboard ${selectedStaff.full_name}`} width={480} onClose={() => !processing && setSelectedStaff(null)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ padding: 14, background: `${T.orange}11`, borderRadius: 10, border: `1px solid ${T.orange}33` }}>
              <div style={{ fontSize: 13, color: T.orange, fontWeight: 800, marginBottom: 8 }}>ASSET RECOVERY CHECKLIST</div>
              {staffAssets.length > 0 ? staffAssets.map(a => (
                <div key={a.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6, color: C.text }}>
                  <span>• {a.asset_name} ({a.asset_type})</span>
                  <span style={{ color: C.muted }}>{a.serial_number || "No Serial"}</span>
                </div>
              )) : <div style={{ fontSize: 12, color: C.muted }}>No assets assigned. Safe to proceed.</div>}
              {staffAssets.length > 0 && <div style={{ fontSize: 11, color: "#F87171", marginTop: 8, fontWeight: 800 }}>⚠️ Proceeding will automatically mark all items above as "Available/Returned".</div>}
            </div>
            
            <div className="g2">
              <div><Lbl>Exit Date</Lbl><input type="date" className="inp" value={offboardForm.exit_date} onChange={e => setOffboardForm({...offboardForm, exit_date: e.target.value})} /></div>
              <div><Lbl>Exit Reason</Lbl>
                <select className="inp" value={offboardForm.exit_reason} onChange={e => setOffboardForm({...offboardForm, exit_reason: e.target.value})}>
                  <option value="">— Select —</option>
                  <option value="Resignation">Resignation</option>
                  <option value="Termination">Termination</option>
                  <option value="End of Contract">End of Contract</option>
                  <option value="Retirement">Retirement</option>
                </select>
              </div>
            </div>
            
            <button className="bp" onClick={handleOffboard} disabled={processing} style={{ marginTop: 10, background: "#F87171", borderColor: "#F87171", color: "#fff" }}>
              {processing ? "Processing..." : "Finalize Offboarding & Deactivate"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
"""

if "function OffboardingManager(" not in content:
    content = content.replace("// ─── ROOT ────────────────────────────────────────────────────────────────────", offboarding_code + "\n// ─── ROOT ────────────────────────────────────────────────────────────────────")

# Add to navigation
if '{ id: "offboarding", icon: "exit", label: "Offboarding" }' not in content:
    content = content.replace('{ id: "admin", icon: "dashboard", label: "Workforce Stats" },', '{ id: "admin", icon: "dashboard", label: "Workforce Stats" },\n    { id: "offboarding", icon: "staff", label: "Offboarding Workflow" },')

# Add routing rendering
if 'if (p === "offboarding") return <OffboardingManager />;' not in content:
    content = content.replace('if (p === "admin") return <Administration />;', 'if (p === "admin") return <Administration />;\n      if (p === "offboarding") return <OffboardingManager />;')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected Offboarding Workflow component")

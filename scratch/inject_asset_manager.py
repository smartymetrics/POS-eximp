
import os

file_path = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\hrm-portal\src\App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

asset_manager_code = """
// ─── ASSET MANAGEMENT ────────────────────────────────────────────────────────
function AssetManager() {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  const [assets, setAssets] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [assignForm, setAssignForm] = useState({ staff_id: "", status: "Assigned", notes: "" });
  const [createForm, setCreateForm] = useState({ asset_name: "", asset_type: "Equipment", serial_number: "", purchase_cost: "" });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [assData, stfData] = await Promise.all([
        apiFetch(`${API_BASE}/hr/assets`),
        apiFetch(`${API_BASE}/hr/staff`)
      ]);
      setAssets(assData || []);
      setStaffList(stfData || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async () => {
    try {
      await apiFetch(`${API_BASE}/hr/assets/${selectedAsset.id}/assign`, {
        method: "PATCH",
        body: JSON.stringify(assignForm)
      });
      setShowAssignModal(false);
      fetchData();
    } catch (e) { alert("Failed to assign: " + e.message); }
  };

  const handleCreate = async () => {
    if (!createForm.asset_name) return alert("Asset name required");
    try {
      await apiFetch(`${API_BASE}/hr/assets`, {
        method: "POST",
        body: JSON.stringify({
          ...createForm,
          purchase_cost: createForm.purchase_cost ? parseFloat(createForm.purchase_cost) : null
        })
      });
      setShowCreateModal(false);
      setCreateForm({ asset_name: "", asset_type: "Equipment", serial_number: "", purchase_cost: "" });
      fetchData();
    } catch (e) { alert("Failed to create: " + e.message); }
  };

  return (
    <div className="fade">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
        <div>
          <div className="ho" style={{ fontSize: 24, marginBottom: 4 }}>Asset Management</div>
          <div style={{ fontSize: 13, color: C.sub }}>Track and assign physical company property across the workforce.</div>
        </div>
        <button className="bp" onClick={() => setShowCreateModal(true)}>+ Register New Asset</button>
      </div>

      <div className="g4" style={{ marginBottom: 22 }}>
        <StatCard label="Total Assets" value={assets.length} />
        <StatCard label="Assigned" value={assets.filter(a => a.status === 'Assigned').length} col="#60A5FA" />
        <StatCard label="Available" value={assets.filter(a => a.status === 'Available').length} col="#4ADE80" />
        <StatCard label="Maintenance" value={assets.filter(a => a.status === 'Maintenance').length} col="#F87171" />
      </div>

      <div className="gc" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tw">
          <table className="ht">
            <thead>
              <tr>
                <th>Asset Details</th>
                <th>Type / Serial</th>
                <th>Status</th>
                <th>Current Assignee</th>
                <th>Fin. Link</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {assets.map(a => (
                <tr key={a.id}>
                  <td>
                    <div style={{ fontWeight: 800, color: C.text }}>{a.asset_name}</div>
                    <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>Added {new Date(a.created_at).toLocaleDateString()}</div>
                  </td>
                  <td>
                    <div style={{ color: C.text }}>{a.asset_type}</div>
                    <div style={{ fontSize: 11, color: C.muted, marginTop: 2, fontFamily: "monospace" }}>{a.serial_number || "N/A"}</div>
                  </td>
                  <td>
                    <span className="tg" style={{ background: a.status === 'Available' ? '#4ADE8022' : a.status === 'Assigned' ? '#60A5FA22' : '#F8717122', color: a.status === 'Available' ? '#4ADE80' : a.status === 'Assigned' ? '#60A5FA' : '#F87171' }}>{a.status}</span>
                  </td>
                  <td>
                    {a.admins ? (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Av av={a.admins.full_name[0]} sz={24} />
                        <div>
                          <div style={{ fontWeight: 700, color: C.text, fontSize: 12 }}>{a.admins.full_name}</div>
                          <div style={{ fontSize: 10, color: C.muted }}>{a.admins.department}</div>
                        </div>
                      </div>
                    ) : <span style={{ color: C.muted, fontStyle: "italic" }}>Unassigned</span>}
                  </td>
                  <td>
                    {a.payout_request_id ? (
                      <span style={{ fontSize: 10, background: `${T.orange}1A`, color: T.orange, padding: "3px 6px", borderRadius: 4, fontWeight: 700 }}>Linked to Payout</span>
                    ) : <span style={{ color: C.muted }}>—</span>}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="bg" style={{ padding: "6px 12px", fontSize: 11 }} onClick={() => {
                      setSelectedAsset(a);
                      setAssignForm({ staff_id: a.assigned_to || "", status: a.status, notes: a.notes || "" });
                      setShowAssignModal(true);
                    }}>Manage</button>
                  </td>
                </tr>
              ))}
              {assets.length === 0 && !loading && (
                <tr><td colSpan="6" style={{ textAlign: "center", padding: 30, color: C.muted }}>No assets registered yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreateModal && (
        <Modal title="Register Asset" width={480} onClose={() => setShowCreateModal(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div><Lbl>Asset Name *</Lbl><input className="inp" value={createForm.asset_name} onChange={e => setCreateForm({...createForm, asset_name: e.target.value})} placeholder="e.g. MacBook Pro M2" /></div>
            <div className="g2">
              <div><Lbl>Asset Type</Lbl>
                <select className="inp" value={createForm.asset_type} onChange={e => setCreateForm({...createForm, asset_type: e.target.value})}>
                  <option>Equipment</option><option>Vehicle</option><option>Property</option><option>Software License</option>
                </select>
              </div>
              <div><Lbl>Serial Number</Lbl><input className="inp" value={createForm.serial_number} onChange={e => setCreateForm({...createForm, serial_number: e.target.value})} placeholder="Optional" /></div>
            </div>
            <div><Lbl>Purchase Cost (Optional)</Lbl><input type="number" className="inp" value={createForm.purchase_cost} onChange={e => setCreateForm({...createForm, purchase_cost: e.target.value})} placeholder="0.00" /></div>
            <button className="bp" onClick={handleCreate} style={{ marginTop: 10 }}>Register Asset</button>
          </div>
        </Modal>
      )}

      {showAssignModal && selectedAsset && (
        <Modal title="Manage Asset Assignment" width={480} onClose={() => setShowAssignModal(false)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ padding: 14, background: `${T.orange}11`, borderRadius: 10, border: `1px solid ${T.orange}33` }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: C.text }}>{selectedAsset.asset_name}</div>
              <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>Serial: {selectedAsset.serial_number || "N/A"}</div>
            </div>
            <div><Lbl>Assign To Staff</Lbl>
              <select className="inp" value={assignForm.staff_id} onChange={e => setAssignForm({...assignForm, staff_id: e.target.value})}>
                <option value="">— Unassigned (Return to Inventory) —</option>
                {staffList.filter(u => u.is_active).map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.department})</option>)}
              </select>
            </div>
            <div><Lbl>Asset Status</Lbl>
              <select className="inp" value={assignForm.status} onChange={e => setAssignForm({...assignForm, status: e.target.value})}>
                <option value="Available">Available</option>
                <option value="Assigned">Assigned</option>
                <option value="Maintenance">Maintenance</option>
                <option value="Retired">Retired</option>
              </select>
            </div>
            <div><Lbl>Assignment Notes</Lbl><textarea className="inp" rows="2" value={assignForm.notes} onChange={e => setAssignForm({...assignForm, notes: e.target.value})} placeholder="Condition details, expected return date, etc." /></div>
            <button className="bp" onClick={handleAssign} style={{ marginTop: 10 }}>Save Assignment</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

"""

if "function AssetManager()" not in content:
    content = content.replace("// ─── ROOT ────────────────────────────────────────────────────────────────────", asset_manager_code + "\n// ─── ROOT ────────────────────────────────────────────────────────────────────")

# Add the route to HRAdminPortal
if '{ id: "assets", icon: "tasks", label: "Asset Management" }' not in content:
    content = content.replace('{ id: "disciplinary", icon: "mis", label: "Disciplinary" },', '{ id: "disciplinary", icon: "mis", label: "Disciplinary" },\n    { id: "assets", icon: "tasks", label: "Asset Management" },')
    content = content.replace('if (p === "disciplinary") return <Disciplinary />;', 'if (p === "disciplinary") return <Disciplinary />;\n      if (p === "assets") return <AssetManager />;')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected AssetManager component")


import os

file_path = r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\hrm-portal\src\App.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

org_chart_code = """
// ─── ORG CHART ───────────────────────────────────────────────────────────────
function OrgChartView({ staff }) {
  const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
  
  // Build the hierarchical tree
  const buildTree = (managerId) => {
    return staff
      .filter(s => (s.line_manager_id || null) === managerId && s.is_active !== false)
      .map(s => ({ ...s, children: buildTree(s.id) }));
  };

  const roots = buildTree(null);

  const renderNode = (node, depth = 0, isLast = false) => (
    <div key={node.id} style={{ marginLeft: depth > 0 ? 40 : 0, position: "relative", marginTop: 16 }}>
      {/* Horizontal connector to parent */}
      {depth > 0 && <div style={{ position: "absolute", left: -30, top: 24, width: 30, height: 2, background: C.border }}></div>}
      
      {/* Vertical connector from parent */}
      {depth > 0 && <div style={{ position: "absolute", left: -30, top: -16, width: 2, height: isLast ? 40 : '100%', background: C.border }}></div>}
      
      <div className="gc" style={{ padding: "12px 20px", display: "flex", alignItems: "center", gap: 14, width: "fit-content", borderLeft: `4px solid ${T.gold}`, minWidth: 260 }}>
        <Av av={node.full_name?.split(" ").map(n => n[0]).join("") || "??"} sz={34} />
        <div>
          <div style={{ fontSize: 14, fontWeight: 800, color: C.text }}>{node.full_name}</div>
          <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>{node.staff_profiles?.[0]?.job_title || node.department || "Staff"}</div>
        </div>
      </div>
      
      {/* Container for children */}
      <div style={{ position: "relative" }}>
        {node.children.map((c, idx) => renderNode(c, depth + 1, idx === node.children.length - 1))}
      </div>
    </div>
  );

  return (
    <div style={{ padding: "20px 10px", overflowX: "auto" }}>
      {roots.length > 0 ? roots.map((r, idx) => renderNode(r, 0, idx === roots.length - 1)) : <div style={{ color: C.muted }}>No active staff hierarchy found.</div>}
    </div>
  );
}

"""

if "function OrgChartView(" not in content:
    content = content.replace("// ─── MODULE: STAFF DIRECTORY ─────────────────────────────────────────────────", org_chart_code + "// ─── MODULE: STAFF DIRECTORY ─────────────────────────────────────────────────")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected OrgChartView")

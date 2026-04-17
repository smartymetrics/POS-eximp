import re
import os

app_path = 'src/App.jsx'
with open(app_path, encoding='utf-8') as f:
    content = f.read()

# 1. Update findStaffForRep (Better matching: Email > Phone > Name)
old_logic_pattern = sorted(re.findall(r'const findStaffForRep = rep => \{.*?return staff\.find\(s => \(s\.full_name \|\| \"\"\)\.toLowerCase\(\)\.includes\(repFirst\) && repFirst\.length > 1\);\s+\};', content, re.DOTALL), key=len, reverse=True)
if old_logic_pattern:
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
    content = content.replace(old_logic_pattern[0], new_match_logic)

# 2. Update Admin Commissions component with Date Filtering
# Note: I already added some part in the last attempt, but it might be partially applied or failed.
# I'll check if [startDate, setStartDate] is already there.

if 'const [startDate, setStartDate]' not in content:
    load_dash_mark = 'const loadDashboard = async () => {'
    state_block = """  const [startDate, setStartDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]);
  const [endDate, setEndDate]     = useState(new Date().toISOString().split('T')[0]);

  """
    content = content.replace(load_dash_mark, state_block + load_dash_mark)

    # API Calls update
    content = content.replace('apiFetch(`${API_BASE}/commission/owed`)', 'apiFetch(`${API_BASE}/commission/owed?start_date=${startDate}&end_date=${endDate}`)')
    content = content.replace('apiFetch(`${API_BASE}/commission/earnings`)', 'apiFetch(`${API_BASE}/commission/earnings?start_date=${startDate}&end_date=${endDate}`)')
    content = content.replace('apiFetch(`${API_BASE}/commission/payouts`)', 'apiFetch(`${API_BASE}/commission/payouts?start_date=${startDate}&end_date=${endDate}`)')

    # Re-run on date change
    content = content.replace('useEffect(() => { loadDashboard(); }, []);', 'useEffect(() => { loadDashboard(); }, [startDate, endDate]);')

    # Date Filter UI in Toolbar
    toolbar_mark = '<div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20, flexWrap:"wrap", gap:10 }}>'
    filter_ui = """<div style={{ display:"flex", alignItems:"center", gap:10, background:C.base, padding:"4px 12px", borderRadius:8, border:`1px solid ${C.border}` }}>
          <div style={{ fontSize:11, color:C.sub, fontWeight:700 }}>PERIOD:</div>
          <input type="date" className="inp" style={{ padding:"4px 8px", fontSize:11, width:130, border:"none", background:"transparent" }} value={startDate} onChange={e=>setStartDate(e.target.value)}/>
          <div style={{ fontSize:11, color:C.sub }}>to</div>
          <input type="date" className="inp" style={{ padding:"4px 8px", fontSize:11, width:130, border:"none", background:"transparent" }} value={endDate} onChange={e=>setEndDate(e.target.value)}/>
        </div>"""
    content = content.replace(toolbar_mark, toolbar_mark + "\n        " + filter_ui)

# 3. Staff Portal Navigation & Component
content = content.replace('{ id:"payslip", icon:"presence", label:"My Payslip" }', '{ id:"payroll", icon:"presence", label:"My Payroll" }')
content = content.replace('if (pg==="payslip")   return <MyPayslip user={user}/>;', 'if (pg==="payroll")   return <StaffPayroll user={user}/>;')

# 4. Insert StaffPayroll Component
staff_payroll_code = """
// ─── MODULE: STAFF PAYROLL & COMMISSIONS ──────────────────────────────────────
function StaffPayroll({ user }) {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [tab, setTab] = useState("payslips");
  const [data, setData] = useState({ payslips: [], commissions: null });
  const [loading, setLoading] = useState(true);
  const [dates, setDates] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth() - 2, 1).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  });

  const fmt = n => n != null ? `₦${Number(n).toLocaleString()}` : "—";

  const loadData = async () => {
    setLoading(true);
    try {
      const [p, c] = await Promise.all([
        apiFetch(`${API_BASE}/hr/payroll/payslips?staff_id=${user.id}`),
        apiFetch(`${API_BASE}/commission/my?start_date=${dates.start}&end_date=${dates.end}`)
      ]);
      setData({ payslips: p, commissions: c });
    } catch (e) { console.error("Staff Payroll Load error:", e); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadData(); }, [dates.start, dates.end]);

  const totalEarnedFiltered = data.commissions?.earnings?.reduce((a, b) => a + parseFloat(b.final_amount), 0) || 0;
  const totalPaidFiltered = data.commissions?.payouts?.reduce((a, b) => a + parseFloat(b.total_amount), 0) || 0;

  return (
    <div className="fade">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", marginBottom:22 }}>
        <div>
          <div className="ho" style={{ fontSize:22 }}>My Payroll & Commissions</div>
          <div style={{ fontSize:13, color:C.sub, marginTop:4 }}>View your monthly payslips and sales commission earnings</div>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:10, background:C.base, padding:"4px 12px", borderRadius:8, border:`1px solid ${C.border}` }}>
          <div style={{ fontSize:11, color:C.sub, fontWeight:700 }}>FILTER:</div>
          <input type="date" className="inp" style={{ padding:"4px 8px", fontSize:11, width:130, border:"none", background:"transparent" }} value={dates.start} onChange={e=>setDates(d=>({...d, start:e.target.value}))}/>
          <div style={{ fontSize:11, color:C.sub }}>to</div>
          <input type="date" className="inp" style={{ padding:"4px 8px", fontSize:11, width:130, border:"none", background:"transparent" }} value={dates.end} onChange={e=>setDates(d=>({...d, end:e.target.value}))}/>
        </div>
      </div>

      <div className="tab-bar" style={{ marginBottom:20 }}>
        <button className={`tab ${tab==="payslips"?"on":"off"}`} onClick={()=>setTab("payslips")}>My Payslips</button>
        <button className={`tab ${tab==="commissions"?"on":"off"}`} onClick={()=>setTab("commissions")}>My Commissions</button>
      </div>

      {loading ? <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading data...</div> : (
        tab === "payslips" ? (
          <div className="gc" style={{ overflow:"hidden" }}>
             {data.payslips.length === 0 ? (
               <div style={{ padding:40, textAlign:"center", color:C.muted }}>No payslips found for this period.</div>
             ) : (
               <div className="tw">
                 <table className="ht">
                   <thead><tr>{['Period', 'Gross Pay', 'Net Pay', 'Status', ''].map(h=><th key={h}>{h}</th>)}</tr></thead>
                   <tbody>
                     {data.payslips.map(p => (
                       <tr key={p.id}>
                         <td style={{ fontWeight:700 }}>{new Date(p.period_start).toLocaleDateString(undefined, {month:'long',year:'numeric'})}</td>
                         <td>{fmt(p.gross_pay)}</td>
                         <td style={{ color:T.orange, fontWeight:800 }}>{fmt(p.net_pay)}</td>
                         <td><span className={`tg ${p.status==="paid"?"tg2":"ty"}`}>{p.status}</span></td>
                         <td><button className="bg" style={{ fontSize:10, padding:"4px 10px" }}>View PDF</button></td>
                       </tr>
                     ))}
                   </tbody>
                 </table>
               </div>
             )}
          </div>
        ) : (
          <div>
            {!data.commissions || !data.commissions.rep_id ? (
              <div className="gc" style={{ padding:40, textAlign:"center", color:C.muted }}>
                <div style={{ fontSize:28, marginBottom:10 }}>🔍</div>
                <div style={{ fontWeight:700 }}>No Sales Rep Profile Linked</div>
                <div style={{ fontSize:13, maxWidth:400, margin:"8px auto" }}>We couldn't find a Sales Rep record matching your email or phone number. Contact HR to link your accounts.</div>
              </div>
            ) : (
              <div>
                 <div className="g3" style={{ marginBottom:20, gap:16 }}>
                    <div className="gc" style={{ padding:18, textAlign:"center" }}>
                       <div style={{ fontSize:10, color:C.sub, textTransform:"uppercase", letterSpacing:"1px", marginBottom:8 }}>Total Owed (Now)</div>
                       <div style={{ fontSize:22, fontWeight:800, color:T.gold }}>{fmt(data.commissions.total_owed)}</div>
                    </div>
                    <div className="gc" style={{ padding:18, textAlign:"center" }}>
                       <div style={{ fontSize:10, color:C.sub, textTransform:"uppercase", letterSpacing:"1px", marginBottom:8 }}>Filtered Earning</div>
                       <div style={{ fontSize:22, fontWeight:800, color:"#10B981" }}>{fmt(totalEarnedFiltered)}</div>
                    </div>
                    <div className="gc" style={{ padding:18, textAlign:"center" }}>
                       <div style={{ fontSize:10, color:C.sub, textTransform:"uppercase", letterSpacing:"1px", marginBottom:8 }}>Payouts (Period)</div>
                       <div style={{ fontSize:22, fontWeight:800, color:"#60A5FA" }}>{fmt(totalPaidFiltered)}</div>
                    </div>
                 </div>

                 <div className="gc" style={{ overflow:"hidden" }}>
                   <div style={{ padding:"14px 20px", borderBottom:`1px solid ${C.border}` }}>
                     <div className="ho" style={{ fontSize:14 }}>Earnings Ledger</div>
                   </div>
                   <div className="tw">
                     <table className="ht">
                       <thead><tr>{['Date', 'Client Info', 'Invoice', 'Amount', 'Status'].map(h=><th key={h}>{h}</th>)}</tr></thead>
                       <tbody>
                         {data.commissions.earnings.map(e => (
                           <tr key={e.id}>
                             <td style={{ fontSize:12, color:C.sub }}>{new Date(e.created_at).toLocaleDateString()}</td>
                             <td>
                               <div style={{ fontWeight:700 }}>{e.clients?.full_name || "—"}</div>
                               <div style={{ fontSize:10, color:C.muted }}>Estate: {e.estate_name}</div>
                             </td>
                             <td style={{ fontSize:11, color:C.sub }}>{e.invoices?.invoice_number || "—"}</td>
                             <td style={{ fontWeight:800, color:T.gold }}>{fmt(e.final_amount)}</td>
                             <td><span className={`tg ${e.is_paid?"tg2":parseFloat(e.amount_paid||0)>0?"ty":"tr"}`}>{e.is_paid?"Paid":parseFloat(e.amount_paid||0)>0?"Partial":"Unpaid"}</span></td>
                           </tr>
                         ))}
                         {data.commissions.earnings.length === 0 && <tr><td colSpan="5" style={{ textAlign:"center", padding:30, color:C.muted }}>No earnings records found for this date range.</td></tr>}
                       </tbody>
                     </table>
                   </div>
                 </div>

                 {data.commissions.payouts.length > 0 && (
                   <div className="gc" style={{ marginTop:24, overflow:"hidden" }}>
                     <div style={{ padding:"14px 20px", borderBottom:`1px solid ${C.border}` }}><div className="ho" style={{ fontSize:14 }}>Recent Payouts</div></div>
                     <div className="tw">
                       <table className="ht">
                         <thead><tr>{['Paid Date', 'Payout Amount', 'Reference', 'Notes'].map(h=><th key={h}>{h}</th>)}</tr></thead>
                         <tbody>
                           {data.commissions.payouts.map(p => (
                             <tr key={p.id}>
                               <td style={{ fontSize:12, color:C.sub }}>{new Date(p.paid_at).toLocaleDateString(undefined, {day:'2-digit',month:'short',year:'numeric'})}</td>
                               <td style={{ fontWeight:800, color:"#10B981" }}>{fmt(p.total_amount)}</td>
                               <td style={{ fontSize:11, color:C.sub }}>{p.reference || "—"}</td>
                               <td style={{ fontSize:11, color:C.muted }}>{p.notes || "—"}</td>
                             </tr>
                           ))}
                         </tbody>
                       </table>
                     </div>
                   </div>
                 )}
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
}
"""

# Insert StaffPayroll before LEAVE MANAGEMENT
if 'function StaffPayroll' not in content:
    content = content.replace('// ─── MODULE: LEAVE MANAGEMENT', staff_payroll_code + "\n\n// ─── MODULE: LEAVE MANAGEMENT")

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updates complete")

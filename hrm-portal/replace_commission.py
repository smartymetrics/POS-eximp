import re

with open('src/App.jsx', encoding='utf-8') as f:
    content = f.read()

start_match = re.search(r'// \u2500+ MODULE: AGENT COMMISSIONS[^\n]*\n', content)
end_match   = re.search(r'\n// \u2500+ MODULE: LEAVE MANAGEMENT', content)

if not start_match or not end_match:
    print("ERROR: Could not find markers"); exit(1)

before = content[:start_match.start()]
after  = content[end_match.start():]  # keep the \n before LEAVE MANAGEMENT

new_block = r"""// ─── MODULE: AGENT COMMISSIONS ──────────────────────────────────────────────
function AgentCommissions() {
  const { dark } = useTheme(); const C = dark?DARK:LIGHT;
  const [owed, setOwed]           = useState([]);
  const [payouts, setPayouts]     = useState([]);
  const [earnings, setEarnings]   = useState([]);
  const [reps, setReps]           = useState([]);
  const [staff, setStaff]         = useState([]);
  const [loading, setLoading]     = useState(true);
  const [cTab, setCTab]           = useState("owed");

  // Global Rate
  const [showRateModal, setShowRateModal]   = useState(false);
  const [defaultRate, setDefaultRate]       = useState("");
  const [savingRate, setSavingRate]         = useState(false);

  // Per-Rep Rate
  const [showRepRateModal, setShowRepRateModal] = useState(false);
  const [repRateTarget, setRepRateTarget]       = useState(null);
  const [repRateEstate, setRepRateEstate]       = useState("");
  const [repRateVal, setRepRateVal]             = useState("");
  const [repRateDate, setRepRateDate]           = useState(new Date().toISOString().split("T")[0]);
  const [savingRepRate, setSavingRepRate]       = useState(false);

  // Payout
  const [showPayoutModal, setShowPayoutModal]   = useState(false);
  const [selectedRep, setSelectedRep]           = useState("");
  const [repEarnings, setRepEarnings]           = useState([]);
  const [earningsLoading, setEarningsLoading]   = useState(false);
  const [selectedEarnings, setSelectedEarnings] = useState({});
  const [payoutAmount, setPayoutAmount]         = useState("");
  const [payoutNotes, setPayoutNotes]           = useState("");
  const [payoutRef, setPayoutRef]               = useState("");
  const [submitting, setSubmitting]             = useState(false);

  const fmt = n => n != null ? `\u20a6${Number(n).toLocaleString()}` : "\u2014";

  const findStaffForRep = rep => {
    const repFirst = (rep.name || "").trim().toLowerCase();
    return staff.find(s => (s.full_name || "").toLowerCase().includes(repFirst) && repFirst.length > 1);
  };

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [o, p, e, r, s] = await Promise.all([
        apiFetch(`${API_BASE}/commission/owed`),
        apiFetch(`${API_BASE}/commission/payouts`),
        apiFetch(`${API_BASE}/commission/earnings`),
        apiFetch(`${API_BASE}/sales-reps`),
        apiFetch(`${API_BASE}/hr/staff`)
      ]);
      setOwed(Array.isArray(o) ? o : []);
      setPayouts(Array.isArray(p) ? p : []);
      setEarnings(Array.isArray(e) ? e : []);
      setReps(Array.isArray(r) ? r : []);
      setStaff(Array.isArray(s) ? s : []);
    } catch(err) { console.error("Commission load error:", err); }
    finally { setLoading(false); }
  };
  useEffect(() => { loadDashboard(); }, []);

  // Global Rate
  const openRateModal = async () => {
    setShowRateModal(true);
    try {
      const d = await apiFetch(`${API_BASE}/commission/default-rate`);
      setDefaultRate(d.rate || "5.0");
    } catch(e) { setDefaultRate("5.0"); }
  };
  const saveDefaultRate = async () => {
    setSavingRate(true);
    try {
      await apiFetch(`${API_BASE}/commission/default-rate`, {
        method: "PATCH",
        body: JSON.stringify({ rate: parseFloat(defaultRate), reason: "Updated via HR Portal" })
      });
      setShowRateModal(false);
    } catch(e) { alert("Failed: " + e.message); }
    finally { setSavingRate(false); }
  };

  // Per-Rep Rate
  const openRepRate = (rep) => {
    setRepRateTarget(rep);
    setRepRateEstate(""); setRepRateVal("");
    setRepRateDate(new Date().toISOString().split("T")[0]);
    setShowRepRateModal(true);
  };
  const saveRepRate = async () => {
    if (!repRateEstate || !repRateVal) return alert("Estate and rate required.");
    setSavingRepRate(true);
    try {
      await apiFetch(`${API_BASE}/commission/rates`, {
        method: "POST",
        body: JSON.stringify({
          sales_rep_id: repRateTarget.id,
          estate_name: repRateEstate,
          rate: parseFloat(repRateVal),
          effective_from: repRateDate,
          reason: "Set via HR Portal"
        })
      });
      setShowRepRateModal(false);
    } catch(e) { alert("Failed: " + e.message); }
    finally { setSavingRepRate(false); }
  };

  // Payout
  const handleRepSelect = async (repId) => {
    setSelectedRep(repId); setRepEarnings([]); setSelectedEarnings({}); setPayoutAmount("");
    if (!repId) return;
    setEarningsLoading(true);
    try {
      const data = await apiFetch(`${API_BASE}/commission/owed/${repId}`);
      setRepEarnings(data);
      const sels = {}; let total = 0;
      data.forEach(e => { sels[e.id] = true; total += (parseFloat(e.final_amount) - (parseFloat(e.amount_paid)||0)); });
      setSelectedEarnings(sels); setPayoutAmount(total.toFixed(2));
    } catch(err) { console.error(err); }
    finally { setEarningsLoading(false); }
  };
  const toggleEarning = id => {
    const next = { ...selectedEarnings, [id]: !selectedEarnings[id] };
    setSelectedEarnings(next);
    let total = 0;
    repEarnings.forEach(e => { if (next[e.id]) total += (parseFloat(e.final_amount) - (parseFloat(e.amount_paid)||0)); });
    setPayoutAmount(total.toFixed(2));
  };
  const submitPayout = async () => {
    if (!selectedRep || parseFloat(payoutAmount) <= 0) return alert("Select rep and valid amount.");
    const earningIds = Object.keys(selectedEarnings).filter(k => selectedEarnings[k]);
    if (!earningIds.length) return alert("Select at least one commission record.");
    setSubmitting(true);
    try {
      await apiFetch(`${API_BASE}/commission/payout`, {
        method: "POST",
        body: JSON.stringify({ sales_rep_id: selectedRep, earning_ids: earningIds, reference: payoutRef, notes: payoutNotes, total_amount: parseFloat(payoutAmount) })
      });
      setShowPayoutModal(false); setSelectedRep(""); setPayoutNotes(""); setPayoutRef(""); setPayoutAmount("");
      loadDashboard();
    } catch(err) { alert("Payout error: " + err.message); }
    finally { setSubmitting(false); }
  };

  if (loading) return <div style={{ padding:40, textAlign:"center", color:C.muted }}>Loading commissions\u2026</div>;

  const totalOwed = owed.reduce((a, o) => a + o.total, 0);
  const totalPaid = payouts.reduce((a, p) => a + parseFloat(p.total_amount||0), 0);

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20, flexWrap:"wrap", gap:10 }}>
        <button className="bg" onClick={openRateModal} style={{ display:"flex", alignItems:"center", gap:6, fontSize:12 }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          Global Rate
        </button>
        <button className="bp" onClick={() => { setSelectedRep(""); setRepEarnings([]); setPayoutAmount(""); setShowPayoutModal(true); }} style={{ display:"flex", alignItems:"center", gap:6, padding:"10px 18px" }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Payout
        </button>
      </div>

      {/* Summary cards */}
      <div className="g3" style={{ marginBottom:24, gap:16 }}>
        <div className="gc" style={{ padding:18, textAlign:"center" }}>
          <div style={{ fontSize:11, color:C.muted, textTransform:"uppercase", letterSpacing:"1px", marginBottom:8 }}>Total Owed</div>
          <div style={{ fontSize:22, fontWeight:800, color:T.gold }}>{fmt(totalOwed)}</div>
          <div style={{ fontSize:10, color:C.sub, marginTop:4 }}>{owed.length} rep{owed.length!==1?"s":""} pending</div>
        </div>
        <div className="gc" style={{ padding:18, textAlign:"center" }}>
          <div style={{ fontSize:11, color:C.muted, textTransform:"uppercase", letterSpacing:"1px", marginBottom:8 }}>Total Disbursed</div>
          <div style={{ fontSize:22, fontWeight:800, color:"#10B981" }}>{fmt(totalPaid)}</div>
          <div style={{ fontSize:10, color:C.sub, marginTop:4 }}>{payouts.length} payout batch{payouts.length!==1?"es":""}</div>
        </div>
        <div className="gc" style={{ padding:18, textAlign:"center" }}>
          <div style={{ fontSize:11, color:C.muted, textTransform:"uppercase", letterSpacing:"1px", marginBottom:8 }}>Active Agents</div>
          <div style={{ fontSize:22, fontWeight:800, color:"#60A5FA" }}>{reps.length}</div>
          <div style={{ fontSize:10, color:C.sub, marginTop:4 }}>{earnings.length} earnings records</div>
        </div>
      </div>

      {/* Inner tabs */}
      <div className="tab-bar" style={{ marginBottom:20 }}>
        <button className={`tab ${cTab==="owed"?"on":"off"}`} onClick={() => setCTab("owed")}>Pending Owed</button>
        <button className={`tab ${cTab==="payouts"?"on":"off"}`} onClick={() => setCTab("payouts")}>Payout History</button>
        <button className={`tab ${cTab==="earnings"?"on":"off"}`} onClick={() => setCTab("earnings")}>All Earnings</button>
      </div>

      {/* Pending Owed */}
      {cTab === "owed" && (
        <div className="gc" style={{ overflow:"hidden" }}>
          {owed.length === 0 ? (
            <div style={{ padding:40, textAlign:"center", color:C.muted }}>
              <div style={{ fontSize:28, marginBottom:10 }}>&#10003;</div>
              <div style={{ fontWeight:700, marginBottom:6 }}>All Caught Up</div>
              <div style={{ fontSize:12 }}>No pending commissions owed across all reps.</div>
            </div>
          ) : owed.map(o => {
            const rep = reps.find(r => r.id === o.rep_id);
            const linked = rep ? findStaffForRep(rep) : null;
            return (
              <div key={o.rep_id} style={{ display:"flex", borderBottom:`1px solid ${C.border}`, padding:16, alignItems:"center", gap:14 }}>
                <Av av={(o.name||"?").substring(0,2).toUpperCase()} sz={40}/>
                <div style={{ flex:1 }}>
                  <div style={{ fontWeight:700, marginBottom:2 }}>{o.name}</div>
                  <div style={{ fontSize:11, color:C.sub }}>
                    {o.count} deal{o.count>1?"s":""}{o.partially_paid ? " \u00b7 Partially collected" : ""}
                    {linked && <span style={{ marginLeft:8, color:T.gold, fontWeight:700 }}>\u00b7 Staff: {linked.full_name}</span>}
                  </div>
                </div>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <div style={{ textAlign:"right" }}>
                    <div style={{ fontWeight:800, color:T.gold, fontSize:15 }}>{fmt(o.total)}</div>
                    <div style={{ fontSize:10, textTransform:"uppercase", color:C.sub }}>Owed</div>
                  </div>
                  <button className="bg" style={{ fontSize:10, padding:"5px 10px", whiteSpace:"nowrap" }} onClick={() => openRepRate({ id: o.rep_id, name: o.name })}>Set Rate</button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Payout History */}
      {cTab === "payouts" && (
        <div className="gc" style={{ overflow:"hidden" }}>
          {payouts.length === 0 ? (
            <div style={{ padding:40, textAlign:"center", color:C.muted }}>
              <div style={{ fontSize:28, marginBottom:10 }}>&#128179;</div>
              <div style={{ fontWeight:700, marginBottom:6 }}>No Payouts Yet</div>
              <div style={{ fontSize:12 }}>Use "New Payout" to process commission payouts.</div>
            </div>
          ) : (
            <div className="tw">
              <table className="ht">
                <thead><tr>{["Rep","Date","Amount","Reference","Processed By"].map(h=><th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {payouts.map(p => {
                    const rep = reps.find(r => r.id === p.sales_rep_id);
                    const linked = rep ? findStaffForRep(rep) : null;
                    return (
                      <tr key={p.id}>
                        <td>
                          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                            <Av av={(p.sales_reps?.name||"?").substring(0,2).toUpperCase()} sz={28}/>
                            <div>
                              <div style={{ fontWeight:700 }}>{p.sales_reps?.name||"Unknown"}</div>
                              {linked && <div style={{ fontSize:10, color:T.gold }}>HR Staff \u2713</div>}
                            </div>
                          </div>
                        </td>
                        <td style={{ color:C.sub, fontSize:12 }}>{new Date(p.paid_at).toLocaleDateString(undefined,{day:"2-digit",month:"short",year:"numeric"})}</td>
                        <td style={{ fontWeight:800, color:"#10B981" }}>{fmt(p.total_amount)}</td>
                        <td style={{ fontSize:12, color:C.sub }}>{p.reference||"\u2014"}</td>
                        <td style={{ fontSize:12, color:C.sub }}>{p.admins?.full_name||"\u2014"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* All Earnings */}
      {cTab === "earnings" && (
        <div className="gc" style={{ overflow:"hidden" }}>
          {earnings.length === 0 ? (
            <div style={{ padding:40, textAlign:"center", color:C.muted }}>
              <div style={{ fontSize:12 }}>No commission earnings found. Commissions are auto-generated when invoices are paid for clients linked to a sales rep.</div>
            </div>
          ) : (
            <div className="tw">
              <table className="ht">
                <thead><tr>{["Rep","Client","Invoice","Commission","Status","Collected"].map(h=><th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {earnings.map(e => {
                    const isPaid = e.is_paid;
                    const amtPaid = parseFloat(e.amount_paid||0);
                    return (
                      <tr key={e.id}>
                        <td style={{ fontWeight:700 }}>{e.sales_reps?.name||"\u2014"}</td>
                        <td style={{ fontSize:12 }}>{e.clients?.full_name||"\u2014"}</td>
                        <td style={{ fontSize:11, color:C.sub }}>{e.invoices?.invoice_number||"\u2014"}</td>
                        <td style={{ fontWeight:700 }}>{fmt(e.final_amount)}</td>
                        <td><span className={`tg ${isPaid?"tg2":amtPaid>0?"ty":"tr"}`}>{isPaid?"Paid":amtPaid>0?"Partial":"Unpaid"}</span></td>
                        <td style={{ fontSize:12 }}>{isPaid ? fmt(e.amount_paid) : amtPaid>0 ? `${fmt(amtPaid)} of ${fmt(e.final_amount)}` : "\u2014"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* MODAL: Global Rate */}
      {showRateModal && (
        <Modal onClose={() => setShowRateModal(false)} title="Global Default Commission Rate">
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ background:C.base, border:`1px solid ${C.border}`, borderRadius:8, padding:14, fontSize:12, color:C.sub, lineHeight:1.6 }}>
              This rate applies to all reps without a custom estate rate. Changes do not affect already-generated earnings.
            </div>
            <div><Lbl>Default Rate (%)</Lbl>
              <input type="number" className="inp" step="0.1" min="0" max="100" value={defaultRate} onChange={e => setDefaultRate(e.target.value)} placeholder="5.0"/></div>
            <button className="bp" onClick={saveDefaultRate} disabled={savingRate} style={{ padding:14 }}>
              {savingRate ? "Saving\u2026" : "Save Global Rate"}
            </button>
          </div>
        </Modal>
      )}

      {/* MODAL: Per-Rep Rate */}
      {showRepRateModal && repRateTarget && (
        <Modal onClose={() => setShowRepRateModal(false)} title={`Custom Rate \u2014 ${repRateTarget.name}`}>
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ background:C.base, border:`1px solid ${C.border}`, borderRadius:8, padding:14, fontSize:12, color:C.sub, lineHeight:1.6 }}>
              Set a custom commission rate for a specific estate. This overrides the global default for this agent on that estate only.
            </div>
            <div><Lbl>Estate Name *</Lbl>
              <input type="text" className="inp" placeholder="e.g. Cloves Estate Phase 2" value={repRateEstate} onChange={e => setRepRateEstate(e.target.value)}/></div>
            <div className="g2" style={{ gap:12 }}>
              <div><Lbl>Rate (%) *</Lbl>
                <input type="number" className="inp" step="0.1" min="0" max="100" placeholder="5.0" value={repRateVal} onChange={e => setRepRateVal(e.target.value)}/></div>
              <div><Lbl>Effective From</Lbl>
                <input type="date" className="inp" value={repRateDate} onChange={e => setRepRateDate(e.target.value)}/></div>
            </div>
            <button className="bp" onClick={saveRepRate} disabled={savingRepRate} style={{ padding:14 }}>
              {savingRepRate ? "Saving\u2026" : "Save Custom Rate"}
            </button>
          </div>
        </Modal>
      )}

      {/* MODAL: Payout */}
      {showPayoutModal && (
        <Modal onClose={() => setShowPayoutModal(false)} title="Process Commission Payout">
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div><Lbl>Select Sales Rep *</Lbl>
              <select className="inp" value={selectedRep} onChange={e => handleRepSelect(e.target.value)}>
                <option value="">\u2014 Choose a Rep \u2014</option>
                {reps.map(r => {
                  const linked = findStaffForRep(r);
                  return <option key={r.id} value={r.id}>{r.name}{r.last_name?" "+r.last_name:""}{linked?" (HR Staff)":""}</option>;
                })}
              </select></div>
            {earningsLoading && <div style={{ fontSize:12, color:C.sub, textAlign:"center", padding:8 }}>Loading unpaid commissions\u2026</div>}
            {!earningsLoading && selectedRep && repEarnings.length===0 && (
              <div style={{ fontSize:12, color:C.muted, textAlign:"center", padding:12, background:C.base, borderRadius:8 }}>No unpaid commissions for this rep.</div>
            )}
            {repEarnings.length > 0 && (
              <div style={{ border:`1px solid ${C.border}`, borderRadius:8, padding:10, maxHeight:220, overflowY:"auto" }}>
                <div style={{ fontSize:11, fontWeight:700, marginBottom:8, color:C.muted, textTransform:"uppercase", letterSpacing:"0.5px" }}>Select earnings to include:</div>
                {repEarnings.map(e => {
                  const bal = parseFloat(e.final_amount) - (parseFloat(e.amount_paid)||0);
                  const isPartial = parseFloat(e.amount_paid||0) > 0;
                  return (
                    <div key={e.id} style={{ display:"flex", alignItems:"center", gap:10, padding:10, background:C.base, borderRadius:6, marginBottom:6, cursor:"pointer" }} onClick={() => toggleEarning(e.id)}>
                      <input type="checkbox" checked={!!selectedEarnings[e.id]} onChange={() => toggleEarning(e.id)} style={{ accentColor:T.gold, width:15, height:15 }}/>
                      <div style={{ flex:1 }}>
                        <div style={{ fontSize:12, fontWeight:700 }}>{e.clients?.full_name||"Unknown"}</div>
                        <div style={{ fontSize:10, color:C.sub }}>Inv: {e.invoices?.invoice_number||"\u2014"}{isPartial?` \u00b7 ${fmt(parseFloat(e.amount_paid||0))} paid`:""}</div>
                      </div>
                      <div style={{ fontWeight:800, color:"#10B981", fontSize:13 }}>{fmt(bal)}</div>
                    </div>
                  );
                })}
              </div>
            )}
            <div className="g2" style={{ gap:12 }}>
              <div><Lbl>Amount to Pay (\u20a6) *</Lbl>
                <input type="number" className="inp" placeholder="0.00" value={payoutAmount} onChange={e => setPayoutAmount(e.target.value)}/></div>
              <div><Lbl>Reference (Optional)</Lbl>
                <input type="text" className="inp" placeholder="TXN-12345" value={payoutRef} onChange={e => setPayoutRef(e.target.value)}/></div>
            </div>
            <div><Lbl>Notes</Lbl>
              <input type="text" className="inp" placeholder="e.g. April 2026 commissions" value={payoutNotes} onChange={e => setPayoutNotes(e.target.value)}/></div>
            <button className="bp" onClick={submitPayout} disabled={submitting} style={{ padding:16, fontSize:14 }}>
              {submitting ? "Processing\u2026" : "Confirm & Process Payout"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
"""

result = before + new_block + after
with open('src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(result)
print("Done. Lines written:", result.count('\n'))

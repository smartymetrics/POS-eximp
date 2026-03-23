/*
 * COMMISSION MANAGEMENT (PRD 4)
 * Injects UI elements into dashboard.html natively to avoid massive HTML edits.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Override global showSection to cleanly integrate Commission views
    if (typeof window.showSection === 'function' && !window._originalShowSection) {
        window._originalShowSection = window.showSection;
        window.showSection = function(name) {
            window._originalShowSection(name);
            const commEl = document.getElementById("section-commission");
            if (commEl) {
                commEl.style.display = (name === 'commission') ? 'block' : 'none';
            }
            if (name === 'commission') {
                document.getElementById('pageTitle').textContent = 'Commission Overview';
                loadCommissionDashboard();
            }
        };
    }

    // 1. Inject Sidebar Nav Item
    const analyticsNav = document.getElementById("nav-analytics");
    if (analyticsNav) {
        const commissionNav = document.createElement("a");
        commissionNav.className = "nav-item admin-only";
        commissionNav.id = "nav-commission";
        commissionNav.href = "#";
        commissionNav.innerHTML = `
            <div style="display:flex; align-items:center; gap:12px; width:100%;">
                <div style="width:24px; height:24px; background:rgba(245,166,35,0.1); border-radius:6px; display:flex; align-items:center; justify-content:center; color:var(--gold);">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <path d="M12 1v22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                    </svg>
                </div>
                <span style="font-weight:600;">Commissions</span>
            </div>
        `;
        commissionNav.onclick = (e) => {
            e.preventDefault();
            document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
            commissionNav.classList.add("active");
            if (typeof window.showSection === 'function') {
                window.showSection('commission');
            }
        };
        analyticsNav.parentNode.insertBefore(commissionNav, analyticsNav.nextSibling);
    }

    // 2. Inject Commission Section Container
    const mainArea = document.querySelector(".main");
    if (mainArea) {
        const commSection = document.createElement("div");
        commSection.className = "content";
        commSection.id = "section-commission";
        commSection.style.display = "none";
        commSection.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="font-size:18px; font-weight:700;">Commission Management</h2>
                <div style="display:flex; gap:10px;">
                    <button class="btn btn-ghost" onclick="openDefaultRateModal()" style="display:flex; align-items:center; gap:6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>
                        Global Rates
                    </button>
                    <button class="btn btn-primary" onclick="openPayoutModal()" style="display:flex; align-items:center; gap:6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                        New Payout
                    </button>
                </div>
            </div>
            
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:24px;">
                <div class="card">
                    <div class="card-header"><span class="card-title">Pending Commissions Owed</span></div>
                    <div class="card-body" style="padding:0; max-height:400px; overflow-y:auto;" id="commissionOwedTable">
                        <div class="loading"><span class="spinner"></span>Loading pending...</div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">Recent Payout Batches</span></div>
                    <div class="card-body" style="padding:0; max-height:400px; overflow-y:auto;" id="commissionPayoutsTable">
                        <div class="loading"><span class="spinner"></span>Loading payouts...</div>
                    </div>
                </div>
            </div>
        `;
        mainArea.appendChild(commSection);
    }

    // 3. Inject Modals
    const modalsContainer = document.createElement("div");
    modalsContainer.innerHTML = `
        <!-- Default Rate Modal -->
        <div class="modal-overlay" id="defaultRateModal">
            <div class="modal">
                <div class="modal-header">
                    <span class="modal-title">Set Global Default Rate</span>
                    <button class="modal-close" onclick="closeModal('defaultRateModal')">&times;</button>
                </div>
                <div class="modal-body">
                    <p style="font-size:12px; color:#666; margin-bottom:16px;">This rate applies automatically to reps if they don't have a specific estate rate set.</p>
                    <div class="form-group" style="margin-bottom:16px;">
                        <label class="form-label">Global Default Rate (%)</label>
                        <input type="number" id="global-rate-input" class="form-control" step="0.1" value="5.0">
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-ghost" onclick="closeModal('defaultRateModal')">Cancel</button>
                        <button class="btn btn-primary" onclick="saveDefaultRate()">Save Rate</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Payout Modal -->
        <div class="modal-overlay" id="payoutModal">
            <div class="modal" style="width: 700px;">
                <div class="modal-header">
                    <span class="modal-title">Process Rep Payout</span>
                    <button class="modal-close" onclick="closeModal('payoutModal')">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-grid" style="margin-bottom:16px;">
                        <div class="form-group span2">
                            <label class="form-label">Select Sales Rep</label>
                            <select id="payout-rep-select" class="form-control" onchange="fetchUnpaidForPayout(this.value)">
                                <option value="">Loading reps...</option>
                            </select>
                        </div>
                    </div>
                    <div id="payout-earnings-list" style="margin-bottom:16px; max-height:250px; overflow-y:auto; border:1px solid #eee; border-radius:6px; padding:10px; display:none;">
                    </div>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Amount to Pay (NGN)</label>
                            <input type="number" id="payout-amount" class="form-control" placeholder="Auto-filled from selection" min="1" step="0.01">
                            <div id="payout-total-hint" style="font-size:11px; color:var(--gray); margin-top:4px;"></div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Reference ID (Optional)</label>
                            <input type="text" id="payout-ref" class="form-control" placeholder="TXN-12345">
                        </div>
                        <div class="form-group span2">
                            <label class="form-label">Notes</label>
                            <input type="text" id="payout-notes" class="form-control" placeholder="March payouts">
                        </div>
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-ghost" onclick="closeModal('payoutModal')">Cancel</button>
                        <button class="btn btn-primary" id="payout-submit-btn" onclick="submitPayout()">Process Payout</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Set Rate Modal -->
        <div class="modal-overlay" id="setRateModal">
            <div class="modal">
                <div class="modal-header">
                    <span class="modal-title">Set Custom Commission Rate</span>
                    <button class="modal-close" onclick="closeModal('setRateModal')">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group" style="margin-bottom:12px;">
                        <label class="form-label">Estate Name</label>
                        <input type="text" id="rate-estate-input" class="form-control" placeholder="e.g. Cloves Estate">
                    </div>
                    <div class="form-group" style="margin-bottom:12px;">
                        <label class="form-label">Custom Rate (%)</label>
                        <input type="number" id="rate-percent-input" class="form-control" step="0.1" value="5.0">
                    </div>
                    <div class="form-group" style="margin-bottom:12px;">
                        <label class="form-label">Effective From</label>
                        <input type="date" id="rate-date-input" class="form-control">
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-ghost" onclick="closeModal('setRateModal')">Cancel</button>
                        <button class="btn btn-primary" onclick="submitSetRate()">Save Rate</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Void Commission Modal -->
        <div class="modal-overlay" id="voidCommissionModal">
            <div class="modal">
                <div class="modal-header">
                    <span class="modal-title">Void Commission Earning</span>
                    <button class="modal-close" onclick="closeModal('voidCommissionModal')">&times;</button>
                </div>
                <div class="modal-body">
                    <p style="font-size:12px; color:var(--red); margin-bottom:16px;"><strong>Warning:</strong> Voiding a commission record will remove it from the rep's owed balance and send them an automated email notification.</p>
                    <div class="form-group" style="margin-bottom:16px;">
                        <label class="form-label">Void Reason <span class="req">*</span></label>
                        <textarea id="void-comm-reason" class="form-control" rows="3" placeholder="e.g. Transaction cancelled by client / Error in calculation"></textarea>
                        <input type="hidden" id="void-comm-id">
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-ghost" onclick="closeModal('voidCommissionModal')">Cancel</button>
                        <button class="btn btn-primary" id="void-comm-btn" style="background:var(--red); color:white;" onclick="submitVoidCommission()">Confirm Void</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modalsContainer);

    // 4. Hook into Rep Profile Modal to add Commission Tabs
    // The user's repo opens "viewRepInfo" modal probably. I'll rely on an interval or observer to inject the tab if it doesn't exist.
    setInterval(() => {
        const repModalHeader = document.querySelector('#editRepModal .modal-header');
        if (repModalHeader && !document.getElementById('rep-tab-commission')) {
            // Found the existing modal, inject our custom Commission Tab
            const tabsContainer = document.querySelector('#editRepModal .modal-body .tabs') || createTabsHoc();
            if (tabsContainer) {
                const commTab = document.createElement("button");
                commTab.className = "tab-btn";
                commTab.id = "rep-tab-commission";
                commTab.innerText = "Commissions";
                commTab.onclick = () => {
                    // Custom logic to show commission view inside rep modal
                    document.querySelectorAll('#editRepModal .tab-content').forEach(el => el.style.display = 'none');
                    document.querySelectorAll('#editRepModal .tab-btn').forEach(el => el.classList.remove('active'));
                    commTab.classList.add('active');
                    
                    let commContent = document.getElementById('rep-content-commission');
                    if (!commContent) {
                        commContent = document.createElement("div");
                        commContent.id = "rep-content-commission";
                        commContent.className = "tab-content";
                        commContent.style.display = "block";
                        commContent.innerHTML = `
                            <div style="display:flex; justify-content:flex-end; margin-bottom:10px;">
                                <button class="btn btn-ghost" onclick="openSetRateModal(window.currentRepId)" style="font-size:12px; padding:6px 10px;">Set Custom Rate</button>
                            </div>
                            <div id="rep-commission-history" style="font-size:13px;"><div class="loading"><span class="spinner"></span>Loading...</div></div>
                        `;
                        const body = document.querySelector('#editRepModal .modal-body');
                        body.appendChild(commContent);
                    } else {
                        commContent.style.display = "block";
                    }
                    if (window.currentRepId) loadRepCommissionHistory(window.currentRepId);
                };
                tabsContainer.appendChild(commTab);
            }
        }
        // Inject Commission Report Card visually into the Reports grid
        const reportsGrid = document.querySelector("#section-reports > div:nth-child(2)");
        if (reportsGrid && reportsGrid.children.length >= 1 && !document.getElementById('card-comm-report')) {
            const commReportCard = document.createElement("div");
            commReportCard.id = "card-comm-report";
            commReportCard.className = "card";
            commReportCard.style.cssText = "border-top:3px solid #F5A623;";
            commReportCard.innerHTML = `
                <div class="card-body" style="padding:20px;">
                <div style="display:flex; align-items:flex-start; gap:12px; margin-bottom:12px;">
                    <div style="width:40px; height:40px; background:rgba(245,166,35,0.12); border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" stroke-width="2"><path d="M12 1v22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    </div>
                    <div>
                    <div style="font-size:14px; font-weight:700; color:var(--dark);">Commission Report</div>
                    <div style="font-size:11px; color:var(--gray); margin-top:3px; line-height:1.4;">Detailed ledger of all commissions earned categorized by Rep and status</div>
                    </div>
                </div>
                <div style="display:flex; gap:8px; margin-top:16px;">
                    <button class="btn btn-primary" style="flex:1; font-size:12px; padding:8px;" onclick="downloadReport(event,'commission_report','pdf')">⬇ PDF</button>
                    <button class="btn btn-ghost" style="flex:1; font-size:12px; padding:8px;" onclick="downloadReport(event,'commission_report','excel')">⬇ Excel</button>
                    <button class="btn btn-ghost" style="font-size:12px; padding:8px 10px;" onclick="openScheduleModal('commission_report')" title="Schedule this report">🕐</button>
                </div>
                </div>
            `;
            reportsGrid.appendChild(commReportCard);
        }

    }, 1000);
});

// Helper: Open Modal by ID (falls back to custom if global doesn't exist)
function openModalCustom(id) {
    const el = document.getElementById(id);
    if(el) el.classList.add("open");
}
function closeModal(id) {
    const el = document.getElementById(id);
    if(el) el.classList.remove("open");
}

/* --- API CALLS --- */

async function loadCommissionDashboard() {
    try {
        const token = localStorage.getItem('ec_token');
        const [owedRes, payoutsRes] = await Promise.all([
            fetch('/api/commission/owed', { headers: { 'Authorization': 'Bearer '+token } }),
            fetch('/api/commission/payouts', { headers: { 'Authorization': 'Bearer '+token } })
        ]);
        
        const owed = await owedRes.json();
        const payouts = await payoutsRes.json();
        
        // Render Owed
        let owedHtml = '<div style="padding:16px; display:flex; flex-direction:column; gap:12px;">';
        if (owed.length === 0) {
            owedHtml = '<div class="search-empty" style="padding:40px;">No pending commissions owed.</div>';
        } else {
            owed.forEach(o => {
                const initials = o.name.split(' ').map(n=>n[0]).join('').slice(0,2).toUpperCase();
                owedHtml += `
                <div style="background:#fff; border:1px solid #f0f0f0; border-radius:8px; padding:12px; cursor:pointer; transition:all 0.2s;" 
                     onmouseover="this.style.borderColor='var(--gold)'; this.style.transform='translateY(-2px)';" 
                     onmouseout="this.style.borderColor='#f0f0f0'; this.style.transform='none';"
                     onclick="if(window.openEditRepModal) openEditRepModal('${o.rep_id}')">
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                        <div style="width:32px; height:32px; background:rgba(245,166,35,0.1); color:var(--gold-dark); border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:800; flex-shrink:0;">${initials}</div>
                        <div style="flex:1;">
                            <div style="font-size:13px; font-weight:700; color:var(--dark);">${o.name}</div>
                            <div style="font-size:10px; color:var(--gray);">${o.count} active deal${o.count > 1 ? 's' : ''}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:13px; font-weight:800; color:var(--gold-dark);">NGN ${o.total.toLocaleString()}</div>
                            <div style="font-size:9px; color:var(--gray); text-transform:uppercase; letter-spacing:0.5px;">Pending Balance</div>
                        </div>
                    </div>
                    ${o.partially_paid ? `
                    <div style="background:#fffbf0; border-radius:4px; padding:4px 8px; display:flex; align-items:center; gap:6px;">
                        <span style="width:6px; height:6px; background:var(--gold); border-radius:50%;"></span>
                        <span style="font-size:10px; color:#b07d10;">Partial collections received</span>
                    </div>` : ''}
                </div>`;
            });
        }
        owedHtml += '</div>';
        document.getElementById('commissionOwedTable').innerHTML = owedHtml;
        

        // Render Payouts
        let ptsHtml = '<div style="padding:16px; display:flex; flex-direction:column; gap:10px;">';
        if (payouts.length === 0) {
            ptsHtml = '<div class="search-empty" style="padding:40px;">No payout batches processed yet.</div>';
        } else {
            payouts.forEach(p => {
                const date = new Date(p.paid_at).toLocaleDateString('en-GB', { day:'2-digit', month:'short' });
                ptsHtml += `
                <div style="background:#fcfcfc; border:1px solid #eee; border-radius:6px; padding:10px; display:flex; align-items:center; gap:12px;">
                    <div style="width:36px; height:36px; background:#fff; border:1px solid #eee; border-radius:4px; display:flex; flex-direction:column; align-items:center; justify-content:center; flex-shrink:0;">
                        <span style="font-size:9px; font-weight:700; color:var(--gray); text-transform:uppercase; line-height:1;">${date.split(' ')[1]}</span>
                        <span style="font-size:14px; font-weight:800; color:var(--dark); line-height:1;">${date.split(' ')[0]}</span>
                    </div>
                    <div style="flex:1;">
                        <div style="font-size:12px; font-weight:700; color:var(--dark);">${p.sales_reps?.name || 'Unknown'}</div>
                        <div style="font-size:10px; color:var(--gray); display:flex; align-items:center; gap:4px;">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>
                            Ref: ${p.reference || '-'}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:13px; font-weight:800; color:var(--green);">NGN ${p.total_amount.toLocaleString()}</div>
                        <div style="font-size:9px; color:var(--gray); text-transform:uppercase;">Disbursed</div>
                    </div>
                </div>`;
            });
        }
        ptsHtml += '</div>';
        document.getElementById('commissionPayoutsTable').innerHTML = ptsHtml;
        
    } catch(err) {
        console.error("Dashboard Comms Error:", err);
    }
}

async function openDefaultRateModal() {
    openModalCustom('defaultRateModal');
    try {
        const res = await fetch('/api/commission/default-rate', { headers: { 'Authorization': 'Bearer '+localStorage.getItem('ec_token') } });
        const data = await res.json();
        if(data.rate) document.getElementById('global-rate-input').value = data.rate;
    } catch(err){}
}

async function saveDefaultRate() {
    const rate = document.getElementById('global-rate-input').value;
    try {
        const res = await fetch('/api/commission/default-rate', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer '+localStorage.getItem('ec_token') },
            body: JSON.stringify({ rate: parseFloat(rate), reason: 'Updated via dashboard' })
        });
        if(res.ok) {
            closeModal('defaultRateModal');
            alert("Default rate updated successfully.");
        } else {
            alert("Failed to update rate.");
        }
    } catch(err){ console.error(err); }
}

async function openPayoutModal() {
    openModalCustom('payoutModal');
    // Fetch reps to populate select
    try {
        const res = await fetch('/api/sales-reps', { headers: { 'Authorization': 'Bearer '+localStorage.getItem('ec_token') } });
        const data = await res.json();
        const sel = document.getElementById('payout-rep-select');
        sel.innerHTML = '<option value="">-- Select a Rep --</option>';
        data.forEach(r => {
            sel.innerHTML += `<option value="${r.id}">${r.name}</option>`;
        });
    } catch(err){}
}

async function fetchUnpaidForPayout(repId) {
    const listDiv = document.getElementById('payout-earnings-list');
    const amountInput = document.getElementById('payout-amount');
    const totalHint = document.getElementById('payout-total-hint');
    if(!repId) { listDiv.style.display = 'none'; amountInput.value = ''; totalHint.textContent = ''; return; }
    
    listDiv.style.display = 'block';
    listDiv.innerHTML = '<div class="loading"><span class="spinner"></span>Fetching unpaid deals...</div>';
    
    try {
        const res = await fetch('/api/commission/owed/'+repId, { headers: { 'Authorization': 'Bearer '+localStorage.getItem('ec_token') } });
        const data = await res.json();
        
        if (data.length === 0) {
            listDiv.innerHTML = '<div style="font-size:12px; color:var(--gray); text-align:center;">No unpaid commissions for this rep.</div>';
            amountInput.value = ''; totalHint.textContent = '';
            return;
        }
        
        let html = '<div style="font-size:11px; font-weight:600; margin-bottom:8px; color:var(--dark);">Select earnings to pay out:</div>';
        data.forEach(e => {
            const amtPaid = parseFloat(e.amount_paid || 0);
            const finalAmt = parseFloat(e.final_amount);
            const balance = finalAmt - amtPaid;
            const progressPct = amtPaid > 0 ? Math.round((amtPaid / finalAmt) * 100) : 0;
            const isPartial = amtPaid > 0;
            
            html += `
            <div style="display:flex; align-items:center; gap:10px; padding:8px; background:#f9f9f9; border-radius:4px; margin-bottom:4px;">
                <input type="checkbox" class="cb-earning" value="${e.id}" data-balance="${balance}" checked style="accent-color:var(--gold);" onchange="updatePayoutTotal()">
                <div style="flex:1;">
                    <span style="font-size:12px; font-weight:600;">${e.clients.full_name}</span> 
                    <span style="font-size:10px; color:var(--gray);">(${e.invoices.invoice_number})</span>
                    ${isPartial ? `<div style="margin-top:3px;"><div style="height:4px; background:#eee; border-radius:2px; overflow:hidden;"><div style="width:${progressPct}%; height:100%; background:var(--gold);"></div></div><span style="font-size:10px; color:var(--gray);">NGN ${amtPaid.toLocaleString()} paid of NGN ${finalAmt.toLocaleString()}</span></div>` : ''}
                </div>
                <div style="text-align:right;">
                    <div style="font-size:12px; font-weight:700; color:var(--green);">NGN ${balance.toLocaleString()} owed</div>
                    ${isPartial ? `<div style="font-size:10px; color:var(--gray);">of NGN ${finalAmt.toLocaleString()} total</div>` : ''}
                </div>
            </div>`;
        });
        listDiv.innerHTML = html;
        updatePayoutTotal();
        
    } catch(err) {
        listDiv.innerHTML = '<div style="color:red; font-size:12px;">Failed to load.</div>';
    }
}

function updatePayoutTotal() {
    const checkboxes = document.querySelectorAll('.cb-earning:checked');
    const total = Array.from(checkboxes).reduce((sum, c) => sum + parseFloat(c.dataset.balance || 0), 0);
    const amountInput = document.getElementById('payout-amount');
    const totalHint = document.getElementById('payout-total-hint');
    amountInput.value = total.toFixed(2);
    amountInput.max = total;
    totalHint.textContent = `Total owed for selected: NGN ${total.toLocaleString('en-NG', {minimumFractionDigits:2})}`;
}


async function submitPayout() {
    const repId = document.getElementById('payout-rep-select').value;
    if(!repId) { alert("Please select a rep"); return; }
    
    const checkboxes = document.querySelectorAll('.cb-earning:checked');
    const earningIds = Array.from(checkboxes).map(c => c.value);
    
    if(earningIds.length === 0) { alert("Please select at least one earning to pay."); return; }
    
    const amountInput = document.getElementById('payout-amount');
    const totalAmount = parseFloat(amountInput.value);
    if(!totalAmount || totalAmount <= 0) { alert("Please enter a valid payment amount"); return; }
    
    const totalSelected = Array.from(checkboxes).reduce((sum, c) => sum + parseFloat(c.dataset.balance || 0), 0);
    if(totalAmount > totalSelected + 0.01) { alert(`Amount cannot exceed total owed (NGN ${totalSelected.toLocaleString()})`); return; }
    
    const ref = document.getElementById('payout-ref').value;
    const notes = document.getElementById('payout-notes').value;
    
    const btn = document.getElementById('payout-submit-btn');
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="border-top-color:currentColor; width:14px; height:14px; margin-right:6px;"></span> Processing...';
    btn.style.opacity = '0.7';
    
    try {
        const res = await fetch('/api/commission/payout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer '+localStorage.getItem('ec_token') },
            body: JSON.stringify({ sales_rep_id: repId, earning_ids: earningIds, reference: ref, notes: notes, total_amount: totalAmount })
        });
        if(res.ok) {
            closeModal('payoutModal');
            alert("Payout processed successfully!");
            loadCommissionDashboard();
        } else {
            const data = await res.json();
            alert("Error: " + (data.detail || "Failed to process payout"));
        }
    } catch(err) { console.error(err); alert("Network error. Please try again."); }
    finally {
        btn.disabled = false;
        btn.innerHTML = origText;
        btn.style.opacity = '1';
    }
}


function openSetRateModal(repId) {
    window._tempRepIdRate = repId;
    document.getElementById('rate-date-input').valueAsDate = new Date();
    openModalCustom('setRateModal');
}

async function submitSetRate() {
    const estate = document.getElementById('rate-estate-input').value;
    const rate = document.getElementById('rate-percent-input').value;
    const date = document.getElementById('rate-date-input').value;
    
    if(!estate || !rate || !date) return alert("Fill all fields");
    
    try {
        const res = await fetch('/api/commission/rates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer '+localStorage.getItem('ec_token') },
            body: JSON.stringify({
                sales_rep_id: window._tempRepIdRate,
                estate_name: estate,
                rate: parseFloat(rate),
                effective_from: date
            })
        });
        if(res.ok) {
            closeModal('setRateModal');
            loadRepCommissionHistory(window._tempRepIdRate);
        }
    } catch(err){}
}

function createTabsHoc() {
    // If the modal didn't have a tabs div, we create one inside modal-body.
    const body = document.querySelector('#editRepModal .modal-body');
    if(!body) return null;
    const tabsRow = document.createElement("div");
    tabsRow.className = "tabs";
    tabsRow.style.cssText = "display:flex; gap:10px; border-bottom:1px solid #eee; margin-bottom:16px;";
    
    // Add default "Overview" tab for existing content
    const kids = Array.from(body.children);
    const existingContent = document.createElement("div");
    existingContent.className = "tab-content";
    kids.forEach(k => existingContent.appendChild(k));
    
    const overTab = document.createElement("button");
    overTab.className = "tab-btn active";
    overTab.innerText = "Overview";
    overTab.onclick = () => {
        document.querySelectorAll('#editRepModal .tab-content').forEach(el => el.style.display = 'none');
        document.querySelectorAll('#editRepModal .tab-btn').forEach(el => el.classList.remove('active'));
        overTab.classList.add('active');
        existingContent.style.display = 'block';
    };
    
    tabsRow.appendChild(overTab);
    body.appendChild(tabsRow);
    body.appendChild(existingContent);
    return tabsRow;
}

// Fallback Rep Commission History render
async function loadRepCommissionHistory(repId) {
    const target = document.getElementById('rep-commission-history');
    if(!target) return;
    target.innerHTML = '<div class="loading"><span class="spinner"></span>Loading...</div>';
    
    try {
        const token = localStorage.getItem('ec_token');
        const [ratesRes, earningsRes] = await Promise.all([
            fetch('/api/commission/rates/'+repId, { headers: { 'Authorization': 'Bearer '+token } }),
            fetch('/api/commission/earnings/rep/'+repId, { headers: { 'Authorization': 'Bearer '+token } })
        ]);
        
        const rates = await ratesRes.json();
        const earnings = await earningsRes.json();
        
        // 1. Calculate Summary Totals
        const unpaidSub = earnings.filter(e => !e.is_paid);
        const paidSub = earnings.filter(e => e.is_paid);
        const totalOwed = unpaidSub.reduce((s, e) => s + (float(e.final_amount) - float(e.amount_paid || 0)), 0);
        const totalPaid = paidSub.reduce((s, e) => s + float(e.final_amount), 0) + unpaidSub.reduce((s, e) => s + float(e.amount_paid || 0), 0);
        const totalEarned = totalOwed + totalPaid;

        function float(v) { return parseFloat(v || 0); }

        let html = `
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:24px;">
                <div style="background:#fff; border:1px solid #eee; border-left:4px solid var(--gold); padding:12px; border-radius:6px; box-shadow:0 2px 4px rgba(0,0,0,0.02);">
                    <div style="font-size:10px; color:var(--gray); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Pending Owed</div>
                    <div style="font-size:16px; font-weight:800; color:var(--gold-dark);">NGN ${totalOwed.toLocaleString()}</div>
                </div>
                <div style="background:#fff; border:1px solid #eee; border-left:4px solid #27ae60; padding:12px; border-radius:6px; box-shadow:0 2px 4px rgba(0,0,0,0.02);">
                    <div style="font-size:10px; color:var(--gray); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Total Paid</div>
                    <div style="font-size:16px; font-weight:800; color:#27ae60;">NGN ${totalPaid.toLocaleString()}</div>
                </div>
                <div style="background:var(--dark); padding:12px; border-radius:6px; box-shadow:0 2px 4px rgba(0,0,0,0.08);">
                    <div style="font-size:10px; color:#aaa; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Cumulative Earnings</div>
                    <div style="font-size:16px; font-weight:800; color:#fff;">NGN ${totalEarned.toLocaleString()}</div>
                </div>
            </div>

            <div style="padding-bottom:12px; border-bottom:2px solid #f8f9fa; margin-bottom:16px; display:flex; align-items:center; justify-content:space-between;">
                <h4 style="margin:0; font-size:13px; font-weight:700; color:var(--dark); display:flex; align-items:center; gap:8px;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    Earning History
                </h4>
                <div style="font-size:11px; color:var(--gray);">${earnings.length} Records</div>
            </div>

            <table class="data-table" style="font-size:12px;">
                <thead>
                    <tr>
                        <th style="padding:10px; background:#f8f9fa;">Date</th>
                        <th style="padding:10px; background:#f8f9fa;">Client / Property</th>
                        <th style="padding:10px; background:#f8f9fa;">Amount</th>
                        <th style="padding:10px; background:#f8f9fa;">Status</th>
                        <th style="padding:10px; background:#f8f9fa; text-align:right;">Actions</th>
                    </tr>
                </thead>
                <tbody>`;

        if(earnings.length === 0) {
            html += '<tr><td colspan="5" class="search-empty" style="padding:40px;">No commission earnings recorded yet.</td></tr>';
        } else {
            earnings.forEach(e => {
                const isPaid = e.is_paid;
                const amtPaid = float(e.amount_paid);
                const finalAmt = float(e.final_amount);
                const balance = finalAmt - amtPaid;
                
                const statusHtml = isPaid 
                    ? '<span class="status paid" style="font-size:10px; padding:2px 8px;">Full Payout</span>' 
                    : (amtPaid > 0 
                        ? `<span class="status partial" style="font-size:10px; padding:2px 8px;">Part Paid (${Math.round(amtPaid/finalAmt*100)}%)</span>` 
                        : '<span class="status unpaid" style="font-size:10px; padding:2px 8px;">Pending</span>');
                
                const dt = new Date(e.created_at).toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' });
                
                let action = '';
                if (!isPaid && !isPaid) {
                    action = `<button class="action-btn" style="color:var(--red); border-color:#feb2b2; font-size:10px; padding:3px 8px;" onclick="openVoidCommissionModal('${e.id}')">Void</button>`;
                }
                
                html += `
                    <tr style="border-bottom:1px solid #f1f5f9; transition:background 0.2s;" onmouseover="this.style.background='#fcfcfc'" onmouseout="this.style.background='transparent'">
                        <td style="color:var(--gray); font-size:11px;">${dt}</td>
                        <td>
                            <div style="font-weight:700; color:var(--dark);">${e.clients?.full_name || 'N/A'}</div>
                            <div style="font-size:10px; color:var(--gray);">${e.invoices?.property_name || e.invoices?.invoice_number || '-'}</div>
                        </td>
                        <td>
                            <div style="font-weight:800; color:var(--dark);">${finalAmt.toLocaleString()}</div>
                            ${amtPaid > 0 ? `<div style="font-size:9px; color:var(--green);">Refined NGN ${amtPaid.toLocaleString()} paid</div>` : ''}
                        </td>
                        <td>${statusHtml}</td>
                        <td style="text-align:right;">${action}</td>
                    </tr>`;
            });
        }
        html += '</tbody></table>';

        if (rates.length > 0) {
            html += `
            <div style="margin-top:32px; padding-top:20px; border-top:1px dashed #eee;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    <span style="font-size:12px; font-weight:700; color:var(--dark); text-transform:uppercase; letter-spacing:0.5px;">Custom Agent Rates</span>
                </div>
                <table class="data-table" style="font-size:11px; background:#fafafa; border-radius:6px; overflow:hidden;">
                    <thead style="background:#f1f5f9;">
                        <tr><th style="padding:6px 12px;">Estate / Region</th><th style="padding:6px 12px;">Comm. Rate</th><th style="padding:6px 12px;">Effective From</th></tr>
                    </thead>
                    <tbody>`;
            rates.forEach(r => {
                if(!r.effective_to) {
                    html += `<tr><td style="padding:8px 12px;">${r.estate_name}</td><td style="padding:8px 12px; font-weight:700; color:var(--gold-dark);">${r.rate}%</td><td style="padding:8px 12px; color:var(--gray);">${r.effective_from}</td></tr>`;
                }
            });
            html += '</tbody></table></div>';
        }
        
        target.innerHTML = html;
        
    } catch(err) { target.innerHTML = "Error loading commissions."; }
}

function openVoidCommissionModal(id) {
    document.getElementById('void-comm-id').value = id;
    document.getElementById('void-comm-reason').value = '';
    openModalCustom('voidCommissionModal');
}

async function submitVoidCommission() {
    const id = document.getElementById('void-comm-id').value;
    const reason = document.getElementById('void-comm-reason').value.trim();
    if (!reason || reason.length < 5) return alert("Please provide a descriptive reason for voiding this commission.");
    
    if (!confirm("Are you SURE you want to void this commission? This action cannot be undone and will notify the sales rep.")) return;

    const btn = document.getElementById('void-comm-btn');
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Voiding...';
    
    try {
        const res = await fetch(`/api/commission/earnings/${id}/void`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('ec_token')
            },
            body: JSON.stringify({ reason })
        });
        
        if (res.ok) {
            closeModal('voidCommissionModal');
            alert("Commission record voided successfully.");
            if (window.currentRepId) loadRepCommissionHistory(window.currentRepId);
            if (document.getElementById("section-commission").style.display === 'block') loadCommissionDashboard();
        } else {
            const data = await res.json();
            alert("Error: " + (data.detail || "Failed to void record"));
        }
    } catch(err) {
        alert("Network error. Please try again.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

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
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 1v22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            Commission
        `;
        commissionNav.onclick = (e) => {
            e.preventDefault();
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
                    <button class="btn btn-ghost" onclick="openDefaultRateModal()">Global Default Rate</button>
                    <button class="btn btn-primary" onclick="openPayoutModal()">+ New Payout</button>
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
    `;
    document.body.appendChild(modalsContainer);

    // 4. Hook into Rep Profile Modal to add Commission Tabs
    // The user's repo opens "viewRepInfo" modal probably. I'll rely on an interval or observer to inject the tab if it doesn't exist.
    setInterval(() => {
        const repModalHeader = document.querySelector('#repModal .modal-header');
        if (repModalHeader && !document.getElementById('rep-tab-commission')) {
            // Found the existing modal, inject our custom Commission Tab
            const tabsContainer = document.querySelector('#repModal .modal-body .tabs') || createTabsHoc();
            if (tabsContainer) {
                const commTab = document.createElement("button");
                commTab.className = "tab-btn";
                commTab.id = "rep-tab-commission";
                commTab.innerText = "Commissions";
                commTab.onclick = () => {
                    // Custom logic to show commission view inside rep modal
                    document.querySelectorAll('#repModal .tab-content').forEach(el => el.style.display = 'none');
                    document.querySelectorAll('#repModal .tab-btn').forEach(el => el.classList.remove('active'));
                    commTab.classList.add('active');
                    
                    let commContent = document.getElementById('rep-content-commission');
                    if (!commContent) {
                        commContent = document.createElement("div");
                        commContent.id = "rep-content-commission";
                        commContent.className = "tab-content";
                        commContent.style.display = "block";
                        commContent.innerHTML = `
                            <div style="display:flex; justify-content:flex-end; margin-bottom:10px;">
                                <button class="btn btn-ghost" onclick="openSetRateModal(currentRepId)" style="font-size:12px; padding:6px 10px;">Set Custom Rate</button>
                            </div>
                            <div id="rep-commission-history" style="font-size:13px;"><div class="loading"><span class="spinner"></span>Loading...</div></div>
                        `;
                        const body = document.querySelector('#repModal .modal-body');
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
        let owedHtml = '<table class="data-table"><thead><tr><th>Rep Name</th><th>Unpaid Deals</th><th>Balance Owed</th></tr></thead><tbody>';
        if (owed.length === 0) owedHtml += '<tr><td colspan="3" class="search-empty">No pending commissions.</td></tr>';
        owed.forEach(o => {
            owedHtml += `<tr>
                <td class="client-name">${o.name}</td>
                <td>${o.count}</td>
                <td style="font-weight:700; color:var(--gold-dark);">
                    NGN ${o.total.toLocaleString()}
                    ${o.partially_paid ? `<div style="font-size:10px; color:var(--gray); font-weight:400; margin-top:2px;">Partial payment applied</div>` : ''}
                </td>
            </tr>`;
        });
        owedHtml += '</tbody></table>';
        document.getElementById('commissionOwedTable').innerHTML = owedHtml;
        

        // Render Payouts
        let ptsHtml = '<table class="data-table"><thead><tr><th>Date</th><th>Rep</th><th>Amount</th><th>Ref</th></tr></thead><tbody>';
        if (payouts.length === 0) ptsHtml += '<tr><td colspan="4" class="search-empty">No layouts processed yet.</td></tr>';
        payouts.forEach(p => {
            const date = new Date(p.paid_at).toLocaleDateString();
            ptsHtml += `<tr>
                <td>${date}</td>
                <td class="client-name">${p.sales_reps?.name || 'Unknown'}</td>
                <td style="font-weight:700; color:var(--green);">NGN ${p.total_amount.toLocaleString()}</td>
                <td style="font-size:11px;">${p.reference || '-'}</td>
            </tr>`;
        });
        ptsHtml += '</tbody></table>';
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
    const body = document.querySelector('#repModal .modal-body');
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
        document.querySelectorAll('#repModal .tab-content').forEach(el => el.style.display = 'none');
        document.querySelectorAll('#repModal .tab-btn').forEach(el => el.classList.remove('active'));
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
        
        let html = '<div style="margin-bottom:20px;"><strong>Active Custom Rates</strong><table class="data-table" style="margin-top:10px;"><thead><tr><th>Estate</th><th>Rate</th><th>Date</th></tr></thead><tbody>';
        if(rates.length === 0) html += '<tr><td colspan="3" class="search-empty">No custom rates. Using system default.</td></tr>';
        rates.forEach(r => {
            if(!r.effective_to) {
                html += `<tr><td>${r.estate_name}</td><td style="font-weight:700;">${r.rate}%</td><td>${r.effective_from}</td></tr>`;
            }
        });
        html += '</tbody></table></div>';
        
        html += '<div><strong>Recent Earning History</strong><table class="data-table" style="margin-top:10px;"><thead><tr><th>Date</th><th>Client</th><th>Amount</th><th>Status</th></tr></thead><tbody>';
        if(earnings.length === 0) html += '<tr><td colspan="4" class="search-empty">No earnings yet.</td></tr>';
        earnings.forEach(e => {
            const status = e.is_paid ? '<span class="status paid">Paid</span>' : '<span class="status unpaid">Unpaid</span>';
            const dt = new Date(e.created_at).toLocaleDateString();
            html += `<tr><td>${dt}</td><td>${e.clients?.full_name||'C'}</td><td style="font-weight:700; color:var(--dark);">NGN ${e.final_amount.toLocaleString()}</td><td>${status}</td></tr>`;
        });
        html += '</tbody></table></div>';
        
        target.innerHTML = html;
        
    } catch(err) { target.innerHTML = "Error loading commissions."; }
}

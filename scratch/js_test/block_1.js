
        let currentTab = 'dashboard';
        let velocityChart = null;
        let allContracts = [];
        const API_BASE = '/api/contracts';
        const HR_LEGAL_API = '/api/hr-legal';
        window.HR_LEGAL_API = HR_LEGAL_API;

        // --- MOBILE NAV ---
        function openMobileNav() {
            document.getElementById('mobileNavDrawer').classList.add('open');
            document.getElementById('mobileNavOverlay').classList.add('open');
            document.body.style.overflow = 'hidden';
        }
        function closeMobileNav() {
            document.getElementById('mobileNavDrawer').classList.remove('open');
            document.getElementById('mobileNavOverlay').classList.remove('open');
            document.body.style.overflow = '';
        }

        function switchTab(tabId, element) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
            document.getElementById(`tab-${tabId}`).classList.remove('hidden');

            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            if (element) {
                element.classList.add('active');
            } else if (event && event.currentTarget) {
                event.currentTarget.classList.add('active');
            }

            currentTab = tabId;
            if (tabId === 'dashboard') {
                fetchSummary();
                fetchExecutionTrends();
            }
            if (tabId === 'execution-portal') fetchContracts();
            if (tabId === 'internal-matters') fetchPersonnelMatters();
            if (tabId === 'external-matters') fetchExternalLegal();
            if (tabId === 'signature-vault') loadAuthorities();
            if (tabId === 'archive') fetchArchive();
            if (tabId === 'notifications') fetchNotifications();
        }

        async function fetchPersonnelMatters() {
            try {
                const res = await fetch(`${HR_LEGAL_API}/matters`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                const internalTypes = ["Personnel", "Employment Contract", "Offer Letter", "NDA", "Disciplinary Notice", "Exit Settlement", "Personnel Policy"];
                const filtered = data.filter(m => internalTypes.includes(m.category));
                renderMatterTable(filtered, 'personnelTableBody');
            } catch (err) { console.error('Personnel fetch error:', err); }
        }

        async function fetchExternalLegal() {
            try {
                const res = await fetch(`${HR_LEGAL_API}/matters`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                const externalTypes = ["External", "Consultancy Agreement", "Freelance Contract", "Vendor Agreement", "Service Agreement", "Partnership Deed", "Other"];
                const filtered = data.filter(m => externalTypes.includes(m.category));
                renderMatterTable(filtered, 'externalTableBody');
            } catch (err) { console.error('External fetch error:', err); }
        }

        function renderMatterTable(data, tableId) {
            const body = document.getElementById(tableId);
            if (!data || data.length === 0) {
                body.innerHTML = '<tr><td colspan="6" class="p-12 text-center text-gray-500 italic">No matters found. Click &quot;Initiate&quot; to start.</td></tr>';
                return;
            }
            body.innerHTML = data.map(m => {
                const displayName = (m.staff && m.staff.full_name) || m.external_party_name || m.title || 'Unknown';
                const drafterName = (m.drafter && m.drafter.full_name) || 'Admin';
                const safeTitle = displayName.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
                const canEdit = !!m.can_edit;
                const canDelete = !!m.can_delete;
                const isDrafter = !!m.is_drafter;
                const editBtn = m.status !== 'Executed'
                    ? canEdit
                        ? `<button onclick="window.location.href=\'/legal/advanced-editor?id=${m.id}\'" class="p-2 bg-brand-gold/10 text-brand-gold rounded hover:bg-brand-gold/20 transition-all flex items-center justify-center w-8 h-8" title="Open Editor">&#9999;&#65039;</button>`
                        : `<button disabled class="p-2 bg-white/5 text-gray-600 rounded flex items-center justify-center w-8 h-8 cursor-not-allowed" title="Read-only — you are not a collaborator">&#128274;</button>`
                    : `<button onclick="copyPersonnelPreviewLink(\'${m.id}\')" class="p-2 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition-all flex items-center justify-center w-8 h-8" title="Share Preview Link">&#128279;</button>`;
                const deleteBtn = canDelete
                    ? `<button onclick="confirmDeleteMatter(\'${m.id}\', \'${safeTitle}\')" class="p-2 bg-red-500/10 text-red-400 rounded hover:bg-red-500/30 transition-all flex items-center justify-center w-8 h-8" title="Delete Matter">&#128465;</button>`
                    : '';
                return `
                <tr class="border-b border-[#2D2F36] hover:bg-white/5 transition group">
                    <td class="px-6 py-4 text-xs font-mono text-brand-gold">${m.id.split('-')[0]}...</td>
                    <td class="px-6 py-4">
                        <p class="text-sm font-bold text-white">${displayName}</p>
                        <p class="text-[10px] text-gray-500">${m.category}</p>
                    </td>
                    <td class="px-6 py-4">
                        <span class="status-badge ${m.status === 'Executed' ? 'status-completed' : 'status-pending'}">${m.status}</span>
                    </td>
                    <td class="px-6 py-4">
                        <p class="text-xs text-gray-300">${drafterName}</p>
                        ${isDrafter ? '<span class="text-[9px] font-bold text-brand-gold uppercase tracking-widest">You</span>' : ''}
                    </td>
                    <td class="px-6 py-4">
                        <div class="flex gap-2 flex-wrap">
                            <button onclick="window.location.href=\'/legal/view?id=${m.id}\'" class="p-2 bg-blue-500/10 text-blue-400 rounded hover:bg-blue-500/20 transition-all flex items-center justify-center w-8 h-8" title="View Document">&#128065;&#65039;</button>
                            ${editBtn}
                            <button onclick="duplicateMatter(\'${m.id}\')" class="p-2 bg-white/5 text-gray-400 rounded hover:bg-white/10 transition-all flex items-center justify-center w-8 h-8" title="Duplicate Matter">&#128111;</button>
                            <button onclick="openAuditTrail(\'${m.id}\')" class="p-2 bg-white/5 text-gray-400 rounded hover:bg-white/10 transition-all flex items-center justify-center w-8 h-8" title="View Audit">&#128220;</button>
                            <button onclick="openVaultPanel(\'${m.id}\', \'${safeTitle}\')" class="p-2 bg-amber-500/10 text-amber-400 rounded hover:bg-amber-500/20 transition-all flex items-center justify-center w-8 h-8" title="Document Hub">&#128206;</button>
                            ${deleteBtn}
                        </div>
                    </td>
                </tr>`;
            }).join('');
        }

        // ── DELETE MATTER ──
        function confirmDeleteMatter(matterId, matterTitle) {
            const modal = document.getElementById('deleteMatterModal');
            document.getElementById('deleteMatterTitle').textContent = matterTitle || matterId;
            document.getElementById('confirmDeleteMatterBtn').onclick = () => deleteMatter(matterId);
            modal.classList.remove('hidden');
        }

        function closeDeleteMatterModal() {
            document.getElementById('deleteMatterModal').classList.add('hidden');
        }

        async function deleteMatter(matterId) {
            closeDeleteMatterModal();
            try {
                const res = await fetch(`${HR_LEGAL_API}/matters/${matterId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                if (!res.ok) {
                    alert(data.detail || 'Failed to delete matter.');
                    return;
                }
                // Refresh whichever tab is active
                if (currentTab === 'internal-matters') fetchPersonnelMatters();
                else if (currentTab === 'external-matters') fetchExternalLegal();
            } catch (err) {
                console.error('Delete error:', err);
                alert('An error occurred while deleting the matter.');
            }
        }

        async function copyPersonnelPreviewLink(matterId) {
            try {
                const res = await fetch(`${HR_LEGAL_API}/matters/${matterId}/preview-link`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                const url = data.preview_url || data.link;
                if (url) {
                    const fullUrl = url.startsWith('http') ? url : `${window.location.origin}${url}`;
                    await navigator.clipboard.writeText(fullUrl);
                    alert('✅ Secure preview link copied to clipboard!\n\nThis link expires in 48 hours.');
                } else {
                    alert('Failed to generate link: ' + (data.detail || 'Unknown error'));
                }
            } catch (err) {
                console.error('Sharing error:', err);
                alert('Connection error while generating link.');
            }
        }

        async function duplicateMatter(matterId) {
            if (!confirm('Duplicate this matter? This will create a new Draft with identical content.')) return;
            try {
                const res = await fetch(`${HR_LEGAL_API}/matters/${matterId}/duplicate`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                if (data.status === 'success') {
                    alert('Matter duplicated successfully!');
                    fetchPersonnelMatters(); // Refresh
                } else {
                    alert('Duplication failed: ' + (data.detail || 'Unknown error'));
                }
            } catch (err) {
                console.error('Duplication error:', err);
                alert('Connection error.');
            }
        }

        async function fetchSummary() {
            try {
                // Fetch from both domains in parallel
                const [legalRes, contractRes] = await Promise.all([
                    fetch(`${HR_LEGAL_API}/summary`, {
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                    }),
                    fetch(`${API_BASE}/summary`, {
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                    })
                ]);

                const legalData = await legalRes.json();
                const contractData = await contractRes.json();

                // 1. Update Legal Matters Pipeline (Gold Section)
                document.getElementById('statMattersTotal').innerText = legalData.total_matters || 0;
                document.getElementById('statMattersDraft').innerText = legalData.draft_matters || 0;
                document.getElementById('statMattersActive').innerText = legalData.active_matters || 0;
                document.getElementById('statMattersExecuted').innerText = legalData.executed_matters || 0;

                // 2. Update Contract Execution Pipeline (Blue Section)
                document.getElementById('statTotal').innerText = contractData.total_contracts || 0;
                document.getElementById('statActive').innerText = contractData.active_sessions || 0;
                document.getElementById('statExecuted').innerText = contractData.executed_contracts || 0;
                document.getElementById('statPending').innerText = contractData.pending_execution || 0;

            } catch (err) {
                console.error('Summary fetch error:', err);
                // Optionally show error state in UI
            }
        }

        async function fetchActivity() {
            try {
                const res = await fetch(`${HR_LEGAL_API}/activity`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                renderActivity(data);
            } catch (err) { console.error('Activity fetch error:', err); }
        }

        async function fetchExecutionTrends() {
            try {
                const res = await fetch(`${HR_LEGAL_API}/execution-trends`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                if (res.ok) {
                    renderExecutionTrends(data);
                } else {
                    console.error('Execution trends error:', data);
                }
            } catch (err) {
                console.error('Execution trends fetch error:', err);
            }
        }

        function renderExecutionTrends(data) {
            const ctx = document.getElementById('velocityChart');
            if (!ctx) return;

            const labels = data.labels || [];
            const initiated = data.initiated || [];
            const executed = data.executed || [];
            const pending = data.pending || [];

            if (velocityChart) {
                velocityChart.destroy();
            }

            velocityChart = new Chart(ctx, {
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Contracts Initiated',
                            data: initiated,
                            type: 'line',
                            borderColor: '#60A5FA',
                            backgroundColor: 'rgba(96,165,250,0.18)',
                            borderWidth: 2,
                            tension: 0.35,
                            fill: false,
                            pointRadius: 4,
                            yAxisID: 'y',
                        },
                        {
                            label: 'Executed Contracts',
                            data: executed,
                            type: 'bar',
                            backgroundColor: '#F59E0B',
                            borderColor: '#F59E0B',
                            borderWidth: 1,
                            yAxisID: 'y',
                        },
                        {
                            label: 'Pending Review',
                            data: pending,
                            type: 'line',
                            borderColor: '#34D399',
                            backgroundColor: 'rgba(52,211,153,0.2)',
                            borderWidth: 2,
                            tension: 0.35,
                            fill: false,
                            pointStyle: 'rectRounded',
                            pointRadius: 4,
                            yAxisID: 'y',
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#E5E7EB',
                                font: { size: 12 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#9CA3AF' },
                            grid: { color: 'rgba(255,255,255,0.06)' },
                        },
                        y: {
                            type: 'linear',
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Volume',
                                color: '#9CA3AF'
                            },
                            ticks: { color: '#9CA3AF' },
                            grid: { color: 'rgba(255,255,255,0.06)' },
                        },
                        y_right: {
                            type: 'linear',
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Hours',
                                color: '#9CA3AF'
                            },
                            ticks: { color: '#9CA3AF' },
                            grid: { drawOnChartArea: false },
                        }
                    }
                }
            });
        }

        function renderActivity(logs) {
            const container = document.getElementById('activityFeed');
            container.innerHTML = (logs || []).map(log => {
                const date = new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `
                    <div class="activity-item flex gap-4">
                        <div class="flex-shrink-0 w-10 h-10 bg-brand-gold/10 rounded-xl flex items-center justify-center text-brand-gold">
                             <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                        </div>
                        <div class="flex-1">
                            <div class="flex justify-between items-start">
                                <p class="text-sm font-bold text-white">${log.description}</p>
                                <span class="text-[10px] text-gray-600 font-bold uppercase">${date}</span>
                            </div>
                            <p class="text-[10px] text-gray-500 uppercase tracking-widest font-bold">BY ${log.performed_by_name || 'SYSTEM'}</p>
                        </div>
                    </div>
                `;
            }).join('');
            if (!logs || logs.length === 0) container.innerHTML = '<p class="text-xs text-gray-500 italic">No recent activity.</p>';
        }

        async function fetchContracts() {
            try {
                const showVoidedEl = document.getElementById('showVoidedToggle');
                const showVoided = showVoidedEl ? showVoidedEl.checked : false;

                // Update toggle UI
                const track = document.getElementById('toggleTrack');
                const thumb = document.getElementById('toggleThumb');
                if (track && thumb) {
                    if (showVoided) {
                        track.classList.remove('bg-gray-700');
                        track.classList.add('bg-brand-gold');
                        thumb.classList.add('translate-x-5');
                    } else {
                        track.classList.add('bg-gray-700');
                        track.classList.remove('bg-brand-gold');
                        thumb.classList.remove('translate-x-5');
                    }
                }

                const res = await fetch(`${API_BASE}/all-contracts?include_voided=${showVoided}`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const contracts = await res.json();
                if (res.ok) {
                    allContracts = contracts || [];
                    renderContracts(allContracts);
                } else {
                    console.error('Contracts error:', contracts);
                }
            } catch (err) { console.error('Contracts fetch error:', err); }
        }

        function filterContracts() {
            const query = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
            if (!query) {
                return renderContracts(allContracts);
            }

            const filtered = allContracts.filter(c => {
                const invoiceId = (c.id || '').toLowerCase();
                const invoiceNumber = (c.invoice_number || '').toLowerCase();
                const clientName = (c.clients?.full_name || '').toLowerCase();
                const clientEmail = (c.clients?.email || '').toLowerCase();
                return invoiceId.includes(query)
                    || invoiceNumber.includes(query)
                    || clientName.includes(query)
                    || clientEmail.includes(query);
            });
            renderContracts(filtered);
        }

        function renderContracts(contracts) {
            const tbody = document.getElementById('contractTableBody');
            const rows = (contracts || []).map(c => {
                const isVoided = c.status === 'voided';
                if (isVoided) {
                    // Filter out voided if toggle changed while rendering (safety)
                    if (!document.getElementById('showVoidedToggle').checked) return '';
                }
                const isClosed = c.contract_closed || c.pipeline_stage === 'closed';
                const statusClass = isClosed ? 'status-completed' : `status-${c.signing_status}`;
                const statusLabel = isVoided ? 'VOIDED' : (isClosed ? 'CLOSED' : c.signing_status);
                const progressWidth = (c.signatures_collected / 3) * 100;
                let actionHtml = '';

                if (isClosed) {
                    actionHtml = '<span class="text-xs text-emerald-400 uppercase font-bold">Closed</span>';
                } else if (c.signing_status === 'completed') {
                    actionHtml = `<button onclick="markContractClosed('${c.id}')" class="bg-emerald-500/10 text-emerald-300 px-3 py-1 rounded-lg text-[10px] font-bold hover:bg-emerald-500 hover:text-white transition uppercase">Mark Closed</button>`;
                } else {
                    actionHtml = `<button onclick="openStatusModal('${c.id}')" class="bg-brand-gold/10 text-brand-gold px-3 py-1 rounded-lg text-[10px] font-bold hover:bg-brand-gold hover:text-white transition uppercase pulse-gold">Manage Execution</button>`;
                }

                return `
                    <tr class="border-b border-[#2D2F36] hover:bg-white/5 transition ${isVoided ? 'opacity-40 grayscale' : ''}" 
                        onclick="if(event.target.tagName !== 'BUTTON' && '${c.status}' !== 'voided') openStatusModal('${c.id}')">
                        <td class="px-6 py-4">
                            <p class="font-bold ${isVoided ? 'text-gray-500 line-through' : 'text-brand-gold'}">${c.invoice_number}</p>
                            <p class="text-[10px] text-gray-500 uppercase">${new Date(c.created_at).toLocaleDateString()}</p>
                        </td>
                        <td class="px-6 py-4">
                            <p class="text-sm font-bold text-white">${c.clients?.full_name || 'N/A'}</p>
                            <p class="text-xs text-gray-500 text-truncate max-w-[150px]">${c.clients?.email || ''}</p>
                        </td>
                        <td class="px-6 py-4">
                            <p class="text-sm text-gray-300 font-bold">${c.property_name}</p>
                            <p class="text-[10px] text-gray-500 uppercase">${c.property_location}</p>
                        </td>
                        <td class="px-6 py-4">
                            <span class="status-badge ${isVoided ? 'bg-gray-800 text-gray-500' : statusClass}">${statusLabel}</span>
                        </td>
                        <td class="px-6 py-4">
                            <div class="w-full bg-gray-800 rounded-full h-1.5 mb-1">
                                <div class="bg-brand-gold h-1.5 rounded-full" style="width: ${progressWidth}%"></div>
                            </div>
                            <p class="text-[10px] text-gray-500">${c.signatures_collected} / 3 Signatures</p>
                        </td>
                        <td class="px-6 py-4 text-xs">
                            ${c.expires_at ? new Date(c.expires_at).toLocaleDateString() : 'N/A'}
                        </td>
                        <td class="px-6 py-4">
                            ${isVoided ? '<span class="text-[10px] text-gray-600 font-bold uppercase italic">No Action</span>' : actionHtml}
                        </td>
                    </tr>
                `;
            }).join('');
            tbody.innerHTML = rows || '<tr><td colspan="7" class="p-12 text-center text-gray-500">No contracts found matching your search.</td></tr>';
        }

        // --- SIGNATURE VAULT CONTROLS ---
        function openSignatureModal(dbRole, title) {
            document.getElementById('modalTitle').innerText = `Manage ${title}`;
            document.getElementById('sigRole').value = dbRole;
            document.getElementById('sigRoleLabel').innerText = `Selected role: ${title}`;
            document.getElementById('sigNameLabel').innerText = dbRole === 'lawyer_seal' ? 'Seal Name' : 'Full Name';
            document.getElementById('sigName').placeholder = dbRole === 'lawyer_seal' ? 'e.g. Eximp & Cloves Seal' : 'e.g. Kolawole Olawale';

            document.getElementById('sigName').value = '';
            document.getElementById('sigAddress').value = '';
            document.getElementById('sigOccupation').value = '';

            const meta = document.getElementById('metaFields');
            if (dbRole === 'company_witness' || dbRole === 'lawyer') {
                meta.classList.remove('hidden');
            } else {
                meta.classList.add('hidden');
            }

            document.getElementById('signatureModal').classList.remove('hidden');
        }
        function closeSignatureModal() { document.getElementById('signatureModal').classList.add('hidden'); }

        async function uploadSignature() {
            const name = document.getElementById('sigName').value;
            const role = document.getElementById('sigRole').value;
            const address = document.getElementById('sigAddress').value;
            const occupation = document.getElementById('sigOccupation').value;
            const file = document.getElementById('sigFile').files[0];
            const btn = document.getElementById('uploadBtn');

            if (!name || !file) return alert('Please provide name and signature file');

            btn.innerText = 'Uploading...';
            btn.disabled = true;

            const reader = new FileReader();
            reader.onloadend = async () => {
                const base64 = reader.result;
                try {
                    const res = await fetch(`${API_BASE}/signatures`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
                        },
                        body: JSON.stringify({
                            full_name: name,
                            role: role,
                            address: address || null,
                            occupation: occupation || null,
                            signature_base64: base64,
                            is_active: true
                        })
                    });
                    if (res.ok) {
                        closeSignatureModal();
                        loadAuthorities();
                    } else {
                        const err = await res.json();
                        alert(err.detail || 'Upload failed');
                    }
                } catch (err) { alert('Upload failed'); }
                finally {
                    btn.innerText = 'Upload & Save';
                    btn.disabled = false;
                }
            };
            reader.readAsDataURL(file);
        }

        async function deactivateSignature(id) {
            if (!confirm('Are you sure you want to deactivate this signature? It will no longer be available for new contracts.')) return;
            try {
                const res = await fetch(`${API_BASE}/signatures/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                if (res.ok) loadAuthorities();
            } catch (err) { alert('Deactivation failed'); }
        }

        function renderAuthorities(data) {
            const roleMap = {
                'director': 'director',
                'secretary': 'secretary',
                'lawyer': 'lawyer',
                'lawyer_seal': 'seal',
                'company_witness': 'witness',
                // Fallbacks just in case
                'Managing Director': 'director',
                'Company Secretary': 'secretary',
                'Authorizing Lawyer': 'lawyer',
                'Lawyer Seal': 'seal',
                'Company Witness': 'witness'
            };

            Object.values(roleMap).forEach(id => {
                const img = document.getElementById(`img-${id}`);
                const empty = document.getElementById(`empty-${id}`);
                const status = document.getElementById(`status-${id}`);
                const nameText = document.getElementById(`name-${id}`);

                const delBtn = document.getElementById(`del-${id}`);

                if (img) img.classList.add('hidden');
                if (empty) empty.classList.remove('hidden');
                if (status) {
                    status.innerText = 'Empty';
                    status.className = 'status-badge bg-gray-800 text-gray-600';
                }
                if (nameText) nameText.innerText = '--';
                if (id === 'witness') {
                    const meta = document.getElementById('meta-witness');
                    if (meta) meta.innerText = '';
                }
                if (delBtn) {
                    delBtn.disabled = true;
                    delete delBtn.dataset.sigId;
                }
            });

            data.filter(s => s.is_active).forEach(sig => {
                const id = roleMap[sig.role];
                if (!id) return;

                const img = document.getElementById(`img-${id}`);
                const empty = document.getElementById(`empty-${id}`);
                const status = document.getElementById(`status-${id}`);
                const nameText = document.getElementById(`name-${id}`);

                const delBtn = document.getElementById(`del-${id}`);

                if (img) {
                    let src = sig.signature_base64 || sig.signature_url || '';
                    if (src && !src.startsWith('http') && !src.startsWith('data:')) {
                        src = `data:image/png;base64,${src}`;
                    }
                    img.src = src;
                    img.classList.remove('hidden');
                }
                if (empty) empty.classList.add('hidden');
                if (status) {
                    status.innerText = 'Active';
                    status.className = 'status-badge status-completed';
                }
                if (nameText) nameText.innerText = sig.full_name || sig.role;

                if (id === 'witness') {
                    const meta = document.getElementById('meta-witness');
                    if (meta) meta.innerText = `${sig.occupation || ''}${sig.occupation && sig.address ? ' • ' : ''}${sig.address || ''}`;
                }

                if (delBtn) {
                    delBtn.dataset.role = id;
                    delBtn.disabled = false;
                }
            });
        }

        async function deleteAuthority(role) {
            if (!role) return;
            if (!confirm('Are you sure you want to delete this signature from the system?')) return;

            try {
                const res = await fetch(`${API_BASE}/signatures/${role}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                if (res.ok) {
                    alert('Signature successfully deleted');
                    loadAuthorities();
                } else {
                    const err = await res.json();
                    alert(err.detail || 'Failed to delete signature.');
                }
            } catch (err) {
                console.error(err);
                alert('Connection error while trying to delete.');
            }
        }

        // --- CONTRACT STATUS MODAL (ORCHESTRATION) ---
        let activeInvoiceId = null;
        let walkInRole = null;

        async function openStatusModal(id) {
            activeInvoiceId = id;
            document.getElementById('statusModal').classList.remove('hidden');
            document.getElementById('statusModalBody').innerHTML = '<div class="py-12 text-center text-gray-500">Loading orchestration data...</div>';

            try {
                const res = await fetch(`${API_BASE}/${id}/status`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                if (!res.ok) throw new Error('Status fetch failed');
                const data = await res.json();
                if (data.status === 'not_started') {
                    renderEmptyStatus();
                } else {
                    renderStatusModal(data);
                }
            } catch (err) {
                console.error(err);
                document.getElementById('statusModalBody').innerHTML = '<div class="py-12 text-center text-red-500 font-bold">Session not found or expired.</div>';
                renderEmptyStatus();
            }
        }

        function closeStatusModal() {
            document.getElementById('statusModal').classList.add('hidden');
            activeInvoiceId = null;
        }

        function renderEmptyStatus() {
            document.getElementById('statusModalInvoice').innerText = "UNAVAILABLE";
            document.getElementById('statusModalBody').innerHTML = `
                <div class="text-center py-12">
                     <div class="w-16 h-16 bg-brand-gold/10 rounded-full flex items-center justify-center mx-auto mb-6">
                        <svg class="w-8 h-8 text-brand-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                     </div>
                     <h4 class="text-xl font-serif mb-2">Initiate Contract Execution</h4>
                     <p class="text-xs text-gray-500 max-w-sm mx-auto mb-8">No active signing session found for this invoice. You need to start the witness signature orchestration workflow.</p>
                     
                     <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto">
                        <button onclick="startSigningSession()" class="px-6 py-3 bg-[#F59E0B] text-black font-semibold rounded-lg hover:brightness-110 transition shadow text-sm">
                            Start Signing Session
                        </button>
                        <button onclick="initiateWalkIn('witness')" class="px-6 py-3 bg-white text-black border border-gray-200 font-semibold rounded-lg hover:bg-gray-50 transition shadow-sm text-sm">
                            Record Walk-in Witness
                        </button>
                         <button onclick="initiateWalkIn('client')" class="px-6 py-3 bg-white text-black border border-gray-200 font-semibold rounded-lg hover:bg-gray-50 transition shadow-sm text-sm">
                            Record Walk-in Client
                        </button>
                        <button onclick="window.location.href='/legal/editor?id='+activeInvoiceId" class="px-6 py-3 bg-white text-[#F59E0B] border border-brand-gold/30 font-semibold rounded-lg hover:bg-orange-50 transition shadow-sm text-sm">
                            Edit Contract Wordings
                        </button>
                     </div>
                </div>
             `;
            document.getElementById('statusModalActions').innerHTML = '';
        }

        function renderStatusModal(data) {
            const hasWitness = data.witness_signatures && data.witness_signatures.length > 0;
            const hasClient = data.client_signed;
            const expires = new Date(data.expires_at).toLocaleDateString();

            document.getElementById('statusModalInvoice').innerText = "ACTIVE ORCHESTRATION";

            let html = `
                <div class="bg-brand-gold/5 border border-brand-gold/20 rounded-2xl p-4 mb-8 flex justify-between items-center group relative overflow-hidden shrink-0">
                    <div class="relative z-10">
                        <p class="text-[10px] font-bold text-brand-gold uppercase tracking-tighter mb-1">ORCHESTRATION ACTIVE</p>
                        <p class="text-[12px] text-gray-300">External verification link is live. Access expires: <span class="text-white font-bold">${expires}</span></p>
                    </div>
                    <div class="flex gap-2 relative z-10">
                        <button onclick="copySigningLink('${data.token}')" class="p-2 bg-black/40 rounded-lg hover:text-brand-gold transition text-[9px] font-bold uppercase tracking-widest">Copy Link</button>
                        <button onclick="resendLink()" class="p-2 bg-black/40 rounded-lg hover:text-brand-gold transition text-[9px] font-bold uppercase tracking-widest">Resend</button>
                        <button onclick="extendSession()" class="p-2 bg-black/40 rounded-lg hover:text-brand-gold transition text-[9px] font-bold uppercase tracking-widest">Extend</button>
                    </div>
                    <div class="absolute inset-0 bg-brand-gold/5 transition-opacity opacity-0 group-hover:opacity-100"></div>
                </div>

                <div class="space-y-4">
                    <h5 class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-4">Execution Pathway</h5>
                    
                    <div class="sig-track-item">
                        <div class="sig-dot ${hasWitness ? 'completed' : 'active'}">
                            ${hasWitness ? '✓' : '1'}
                        </div>
                        <div class="flex justify-between items-center">
                            <div>
                                <p class="text-sm font-bold text-white">${hasWitness ? data.witness_signatures[0].full_name : 'External Witness'}</p>
                                <p class="text-[10px] ${hasWitness ? 'text-emerald-400' : 'text-gray-500'} font-bold uppercase tracking-widest">${hasWitness ? 'VERIFIED' : 'WAITING FOR SIGNATURE'}</p>
                            </div>
                            <div class="flex gap-2">
                                ${hasWitness ? `
                                <button onclick="toggleDetails('witness')" class="px-2 py-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded text-[9px] font-bold border border-white/10 transition uppercase tracking-widest">Details</button>
                                <button onclick="toggleRejectForm('witness', '${data.witness_signatures[0].id}')" class="px-2 py-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded text-[9px] font-bold border border-red-500/20 transition uppercase tracking-widest">Reject</button>
                                ` : ''}
                            </div>
                        </div>
                        ${hasWitness ? `
                        <div id="details-witness" class="hidden mt-2 p-4 bg-white/[0.02] border border-white/5 rounded-xl text-xs text-gray-300 space-y-3 ml-2">
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Email</span>
                                    <span class="text-white font-medium">${data.witness_signatures[0].witness_email}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Occupation</span>
                                    <span class="text-white font-medium">${data.witness_signatures[0].occupation}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Relationship to Parties</span>
                                    <span class="text-white font-medium">${data.witness_signatures[0].relationship_to_parties || 'N/A'}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">IP Address</span>
                                    <span class="text-white font-medium">${data.witness_signatures[0].ip_address || 'N/A'}</span>
                                </div>
                                <div class="col-span-2">
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Address</span>
                                    <span class="text-white font-medium">${data.witness_signatures[0].address}</span>
                                </div>
                                <div class="col-span-2">
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Signed At</span>
                                    <span class="text-white font-medium">${new Date(data.witness_signatures[0].signed_at).toLocaleString()}</span>
                                </div>
                            </div>
                            <div class="pt-2 border-t border-white/5">
                                <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-1">Witness Signature</span>
                                <div class="bg-white p-2 rounded-lg border border-white/10 inline-block cursor-zoom-in" onclick="openImageZoom('${data.witness_signatures[0].signature_base64}')">
                                    <img src="${data.witness_signatures[0].signature_base64}" alt="Witness Signature" class="h-16 max-w-xs object-contain" />
                                </div>
                            </div>
                        </div>
                        ` : ''}
                        ${hasWitness ? `
                        <div id="reject-form-witness-${data.witness_signatures[0].id}" class="hidden mt-2 p-3 bg-red-500/5 border border-red-500/10 rounded-xl space-y-2">
                            <p class="text-[9px] font-bold text-red-400 uppercase tracking-widest">Reason for Witness Rejection</p>
                            <textarea id="reject-reason-witness-${data.witness_signatures[0].id}" class="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-red-500/40" rows="2" placeholder="e.g., Signature unclear or details mismatch..."></textarea>
                            <div class="flex justify-end gap-2">
                                <button onclick="toggleRejectForm('witness', '${data.witness_signatures[0].id}')" class="px-2 py-1 text-[9px] text-gray-400 font-bold hover:text-white uppercase tracking-widest transition">Cancel</button>
                                <button onclick="submitWitnessRejection('${data.witness_signatures[0].id}')" class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-[9px] font-bold uppercase tracking-widest transition">Confirm Rejection</button>
                            </div>
                        </div>
                        ` : ''}
                    </div>

                    <div class="sig-track-item">
                        <div class="sig-dot ${hasClient ? 'completed' : (hasWitness ? 'active' : '')}">
                            ${hasClient ? '✓' : '2'}
                        </div>
                        <div class="flex justify-between items-center">
                            <div>
                                <p class="text-sm font-bold text-white">Purchaser (Client)</p>
                                <p class="text-[10px] ${hasClient ? 'text-emerald-400' : 'text-gray-500'} font-bold uppercase tracking-widest">${hasClient ? 'VERIFIED' : 'WAITING FOR SIGNATURE'}</p>
                            </div>
                            <div class="flex gap-2">
                                ${hasClient ? `
                                <button onclick="toggleDetails('client')" class="px-2 py-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded text-[9px] font-bold border border-white/10 transition uppercase tracking-widest">Details</button>
                                <button onclick="toggleRejectForm('client')" class="px-2 py-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded text-[9px] font-bold border border-red-500/20 transition uppercase tracking-widest">Reject</button>
                                ` : ''}
                            </div>
                        </div>
                        ${hasClient ? `
                        <div id="details-client" class="hidden mt-2 p-4 bg-white/[0.02] border border-white/5 rounded-xl text-xs text-gray-300 space-y-3 ml-2">
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Full Name</span>
                                    <span class="text-white font-medium">${data.client_details?.full_name || 'N/A'}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Email</span>
                                    <span class="text-white font-medium">${data.client_details?.email || 'N/A'}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Phone</span>
                                    <span class="text-white font-medium">${data.client_details?.phone || 'N/A'}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Address</span>
                                    <span class="text-white font-medium">${data.client_details?.address || 'N/A'}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">NIN</span>
                                    <span class="text-white font-medium">${data.client_details?.nin || 'N/A'}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">ID Number</span>
                                    <span class="text-white font-medium">${data.client_details?.id_number || 'N/A'}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Signing Method</span>
                                    <span class="text-white font-medium uppercase">${data.client_signature_method || 'drawn'}</span>
                                </div>
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">IP Address</span>
                                    <span class="text-white font-medium">${data.client_audit_ip || 'N/A'}</span>
                                </div>
                                <div class="col-span-2">
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-0.5">Signed At</span>
                                    <span class="text-white font-medium">${data.client_signed_at ? new Date(data.client_signed_at).toLocaleString() : 'N/A'}</span>
                                </div>
                            </div>
                            
                            ${(data.client_details?.passport_photo_url || data.client_details?.id_document_url) ? `
                            <div class="pt-3 border-t border-white/5 grid grid-cols-2 gap-3">
                                ${data.client_details.passport_photo_url ? `
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-1">Passport Photo</span>
                                    <div class="bg-white/5 p-1 rounded-lg border border-white/10 inline-block">
                                        <img src="${data.client_details.passport_photo_url}" alt="Passport Photo" class="h-16 max-w-full object-contain cursor-zoom-in hover:brightness-110 transition" onclick="openImageZoom(this.src)" />
                                    </div>
                                </div>
                                ` : ''}
                                ${data.client_details.id_document_url ? `
                                <div>
                                    <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-1">ID Document</span>
                                    <div class="bg-white/5 p-1 rounded-lg border border-white/10 inline-block">
                                        <img src="${data.client_details.id_document_url}" alt="ID Document" class="h-16 max-w-full object-contain cursor-zoom-in hover:brightness-110 transition" onclick="openImageZoom(this.src)" />
                                    </div>
                                </div>
                                ` : ''}
                            </div>
                            ` : ''}

                            <div class="pt-3 border-t border-white/5">
                                <span class="text-gray-500 text-[9px] uppercase font-bold tracking-wider block mb-1">Purchaser Signature</span>
                                <div class="bg-white p-2 rounded-lg border border-white/10 inline-block cursor-zoom-in" onclick="openImageZoom('${data.client_signature_url}')">
                                    <img src="${data.client_signature_url}" alt="Client Signature" class="h-16 max-w-xs object-contain" />
                                </div>
                            </div>
                        </div>
                        ` : ''}
                        ${hasClient ? `
                        <div id="reject-form-client" class="hidden mt-2 p-3 bg-red-500/5 border border-red-500/10 rounded-xl space-y-2">
                            <p class="text-[9px] font-bold text-red-400 uppercase tracking-widest">Reason for Client Rejection</p>
                            <textarea id="reject-reason-client" class="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-red-500/40" rows="2" placeholder="e.g., Signature unclear or incorrect signatory..."></textarea>
                            <div class="flex justify-end gap-2">
                                <button onclick="toggleRejectForm('client')" class="px-2 py-1 text-[9px] text-gray-400 font-bold hover:text-white uppercase tracking-widest transition">Cancel</button>
                                <button onclick="submitClientRejection()" class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-[9px] font-bold uppercase tracking-widest transition">Confirm Rejection</button>
                            </div>
                        </div>
                        ` : ''}
                    </div>

                    <div class="sig-track-item">
                        <div class="sig-dot border-gray-700 text-gray-700">3</div>
                        <div>
                            <p class="text-sm font-bold text-gray-400">Legal Authority</p>
                            <p class="text-[10px] text-gray-600 font-bold uppercase tracking-widest">SEALED UPON EXECUTION</p>
                        </div>
                    </div>
                </div>
            `;
            document.getElementById('statusModalBody').innerHTML = html;

            // Actions
            let actionsHtml = `
                <button onclick="window.location.href='/legal/editor?id='+activeInvoiceId" class="px-6 py-2 bg-white/5 border border-brand-gold/30 text-brand-gold rounded-xl text-xs font-bold hover:bg-white/10 transition">Edit Wordings</button>
                <button onclick="viewDraft('${activeInvoiceId}')" class="px-6 py-2 bg-white/5 border border-white/10 rounded-xl text-xs font-bold hover:bg-white/10 transition">View Draft (HTML)</button>
            `;
            if (hasWitness && hasClient) {
                actionsHtml += `<button onclick="openExecutionModal('${activeInvoiceId}')" class="px-6 py-2 bg-brand-gold text-white rounded-xl text-xs font-bold shadow-lg hover:brightness-110 transition pulse-gold">Final Execution</button>`;
                if (!(data.contract_closed || data.pipeline_stage === 'closed')) {
                    actionsHtml += `<button onclick="markContractClosed('${activeInvoiceId}')" class="px-6 py-2 bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-lg hover:brightness-110 transition ml-2">Mark Closed</button>`;
                } else {
                    actionsHtml += `<span class="inline-flex items-center px-4 py-2 bg-emerald-700/10 text-emerald-200 rounded-xl text-xs font-bold uppercase tracking-wider">Closed</span>`;
                }
            } else {
                if (!hasWitness) actionsHtml += `<button onclick="initiateWalkIn('witness')" class="px-4 py-2 bg-white/5 rounded-xl text-[10px] font-bold hover:bg-white/10 transition uppercase tracking-widest whitespace-nowrap">Walk-in Witness</button>`;
                if (!hasClient) actionsHtml += `<button onclick="initiateWalkIn('client')" class="px-4 py-2 bg-white/5 rounded-xl text-[10px] font-bold hover:bg-white/10 transition uppercase tracking-widest whitespace-nowrap">Walk-in Client</button>`;
            }
            document.getElementById('statusModalActions').innerHTML = actionsHtml;
        }

        function toggleDetails(type) {
            const el = document.getElementById(`details-${type}`);
            if (el) el.classList.toggle('hidden');
        }

        function openImageZoom(src) {
            const modal = document.getElementById('imageZoomModal');
            const img = document.getElementById('zoomImage');
            if (modal && img) {
                img.src = src;
                modal.classList.remove('hidden');
            }
        }

        function closeImageZoom() {
            const modal = document.getElementById('imageZoomModal');
            if (modal) {
                modal.classList.add('hidden');
            }
        }

        function toggleRejectForm(type, id = '') {
            const elId = type === 'witness' ? `reject-form-witness-${id}` : 'reject-form-client';
            const el = document.getElementById(elId);
            if (el) {
                el.classList.toggle('hidden');
            }
        }

        async function submitClientRejection() {
            const reasonEl = document.getElementById('reject-reason-client');
            const reason = reasonEl.value.trim();
            if (!reason) {
                alert('Please enter a reason for rejecting the client signature.');
                return;
            }
            
            if (!confirm('Are you sure you want to reject the client signature? This will clear the signature and notify the client.')) {
                return;
            }
            
            try {
                const res = await fetch(`/api/contracts/${activeInvoiceId}/reject-client-signature`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
                    },
                    body: JSON.stringify({ reason: reason })
                });
                const result = await res.json();
                if (res.ok) {
                    alert('Client signature rejected successfully.');
                    openStatusModal(activeInvoiceId);
                } else {
                    alert(result.detail || 'Failed to reject client signature.');
                }
            } catch (err) {
                alert('An error occurred while rejecting client signature.');
            }
        }

        async function submitWitnessRejection(witnessId) {
            const reasonEl = document.getElementById(`reject-reason-witness-${witnessId}`);
            const reason = reasonEl.value.trim();
            if (!reason) {
                alert('Please enter a reason for rejecting the witness signature.');
                return;
            }
            
            if (!confirm('Are you sure you want to reject the witness signature? This will delete the signature and notify the witness and client.')) {
                return;
            }
            
            try {
                const res = await fetch(`/api/contracts/${activeInvoiceId}/witness/${witnessId}/reject`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
                    },
                    body: JSON.stringify({ reason: reason })
                });
                const result = await res.json();
                if (res.ok) {
                    alert('Witness signature rejected successfully.');
                    openStatusModal(activeInvoiceId);
                } else {
                    alert(result.detail || 'Failed to reject witness signature.');
                }
            } catch (err) {
                alert('An error occurred while rejecting witness signature.');
            }
        }

        async function startSigningSession() {
            const btn = event.currentTarget;
            const originalText = btn.innerHTML;
            try {
                btn.disabled = true;
                btn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Starting...`;
                const res = await fetch(`${API_BASE}/session/${activeInvoiceId}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                if (res.ok) openStatusModal(activeInvoiceId);
                else alert(data.detail || 'Failed to start session. Ensure company signatures are set.');
            } catch (err) { alert('Action failed'); }
            finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }

        async function extendSession() {
            try {
                const res = await fetch(`${API_BASE}/${activeInvoiceId}/extend`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                if (res.ok) {
                    alert('Session extended by 48 hours');
                    openStatusModal(activeInvoiceId);
                }
            } catch (err) { alert('Extension failed'); }
        }

        async function resendLink() {
            try {
                const res = await fetch(`${API_BASE}/resend/${activeInvoiceId}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                if (res.ok) alert('Signing link resent to client email.');
            } catch (err) { alert('Action failed'); }
        }

        function copySigningLink(token) {
            const url = `${window.location.origin}/sign-contract?token=${token}`;
            if (navigator.clipboard) {
                navigator.clipboard.writeText(url).then(() => alert('Signing link copied to clipboard')).catch(() => alert('Link: ' + url));
            } else { alert('Link: ' + url); }
        }

        async function markContractClosed(id) {
            if (!confirm('Mark this Contract of Sale as legally closed for the lawyer team? This will not change the sales pipeline stage.')) return;

            try {
                const res = await fetch(`${API_BASE}/${id}/mark-closed`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                if (res.ok) {
                    alert(data.message || 'Contract marked closed');
                    fetchContracts();
                    if (id === activeInvoiceId) openStatusModal(id);
                } else {
                    alert(data.detail || 'Unable to mark contract closed');
                }
            } catch (err) {
                console.error(err);
                alert('Action failed due to connection error.');
            }
        }

        function viewDraft(id) {
            window.open(`/api/contracts/${id}/html-draft?token=${localStorage.getItem('ec_token')}`, '_blank');
        }

        // --- WALK-IN LOGIC ---
        function initiateWalkIn(role) {
            walkInRole = role;
            document.getElementById('walkInModal').classList.remove('hidden');
            document.getElementById('walkInTitle').innerText = role === 'witness' ? 'Record Walk-in Witness' : 'Record Walk-in Client';
            document.getElementById('witnessInfoFields').classList.toggle('hidden', role !== 'witness');
            clearCanvas();
        }

        function closeWalkInModal() {
            document.getElementById('walkInModal').classList.add('hidden');
            walkInRole = null;
        }

        // --- SIGNATURE PAD LOGIC ---
        const canvas = document.getElementById('sig-canvas');
        const ctx = canvas.getContext('2d');
        let painting = false;

        function startPosition(e) {
            painting = true;
            draw(e);
        }
        function finishedPosition() {
            painting = false;
            ctx.beginPath();
        }
        function draw(e) {
            if (!painting) return;
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';
            ctx.strokeStyle = '#1e293b';

            const rect = canvas.getBoundingClientRect();
            const x = ((e.clientX || (e.touches && e.touches[0].clientX)) - rect.left);
            const y = ((e.clientY || (e.touches && e.touches[0].clientY)) - rect.top);

            ctx.lineTo(x, y);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x, y);
        }
        canvas.addEventListener('mousedown', startPosition);
        canvas.addEventListener('touchstart', (e) => { e.preventDefault(); startPosition(e); });
        canvas.addEventListener('mouseup', finishedPosition);
        canvas.addEventListener('touchend', finishedPosition);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('touchmove', (e) => { e.preventDefault(); draw(e); });

        function clearCanvas() { ctx.clearRect(0, 0, canvas.width, canvas.height); }

        async function saveWalkInSignature() {
            const btn = document.getElementById('saveWalkInBtn');
            const dataUrl = canvas.toDataURL('image/png');

            const payload = {
                signature_base64: dataUrl,
                signature_method: 'digital'
            };

            if (walkInRole === 'witness') {
                payload.full_name = document.getElementById('walkInName').value;
                payload.email = document.getElementById('walkInEmail').value;
                if (!payload.full_name) return alert('Legal name is required for witness');
            }

            btn.innerText = 'Capturing...';
            btn.disabled = true;

            try {
                const endpoint = walkInRole === 'witness' ? 'manual-witness' : 'manual-client';
                const res = await fetch(`${API_BASE}/${activeInvoiceId}/${endpoint}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
                    },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    closeWalkInModal();
                    openStatusModal(activeInvoiceId);
                } else {
                    const err = await res.json();
                    alert(err.detail || 'Capture failed');
                }
            } catch (err) { alert('Connection error'); }
            finally {
                btn.innerText = 'Capture & Save';
                btn.disabled = false;
            }
        }

        function openExecutionModal(id) {
            document.getElementById('customSealFile').value = '';
            document.getElementById('sealedPdfFile').value = '';
            document.getElementById('sealedUploadStatus').classList.add('hidden');

            const sendBtn = document.getElementById('sendSealedBtn');
            sendBtn.disabled = true;
            sendBtn.classList.add('opacity-30', 'cursor-not-allowed');

            document.getElementById('executionModal').classList.remove('hidden');
        }
        function closeExecutionModal() { document.getElementById('executionModal').classList.add('hidden'); }

        async function executeContract() {
            const btn = document.getElementById('confirmExecuteBtn');
            btn.innerText = 'Executing...';
            btn.disabled = true;

            try {
                // If custom seal is uploaded, push it first
                const sealFile = document.getElementById('customSealFile').files[0];
                if (sealFile) {
                    btn.innerText = 'Uploading Seal...';
                    const sealData = new FormData();
                    sealData.append('file', sealFile);
                    await fetch(`${API_BASE}/${activeInvoiceId}/seal`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` },
                        body: sealData
                    });
                }

                btn.innerText = 'Finalizing...';
                const sendCert = document.getElementById('sendCertToggle').checked;
                const res = await fetch(`${API_BASE}/execute/${activeInvoiceId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
                    },
                    body: JSON.stringify({ send_certificate: sendCert })
                });

                if (res.ok) {
                    alert('Contract fully executed and archived.');
                    closeExecutionModal();
                    closeStatusModal();
                    fetchContracts();
                } else {
                    const err = await res.json();
                    alert(err.detail || 'Execution failed');
                }
            } catch (err) { alert('Execution failed'); }
            finally {
                btn.innerText = 'VERIFY & EXECUTE';
                btn.disabled = false;
            }
        }

        function downloadSealingPDF() {
            window.location.href = `${API_BASE}/download-sealing/${activeInvoiceId}?token=${localStorage.getItem('ec_token')}`;
        }

        async function uploadSealedPDF() {
            const file = document.getElementById('sealedPdfFile').files[0];
            if (!file) return alert('Please select a PDF file to upload.');

            const btn = document.getElementById('uploadSealedBtn');
            btn.innerText = 'Uploading...';
            btn.disabled = true;

            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch(`${API_BASE}/upload-sealed/${activeInvoiceId}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` },
                    body: formData
                });

                if (res.ok) {
                    document.getElementById('sealedUploadStatus').classList.remove('hidden');
                    const sendBtn = document.getElementById('sendSealedBtn');
                    sendBtn.disabled = false;
                    sendBtn.classList.remove('opacity-30', 'cursor-not-allowed');
                } else {
                    const err = await res.json();
                    alert(err.detail || 'Upload failed');
                }
            } catch (err) {
                alert('Upload failed due to connection error.');
            } finally {
                btn.innerText = 'Upload';
                btn.disabled = false;
            }
        }

        async function sendSealedPDF() {
            const btn = document.getElementById('sendSealedBtn');
            btn.innerText = 'Sending...';
            btn.disabled = true;

            const sendCert = document.getElementById('sendCertToggle').checked;

            try {
                const res = await fetch(`${API_BASE}/send-sealed/${activeInvoiceId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
                    },
                    body: JSON.stringify({ send_certificate: sendCert })
                });

                if (res.ok) {
                    alert('Sealed contract finalized, archived, and emailed to the client.');
                    closeExecutionModal();
                    closeStatusModal();
                    fetchContracts();
                } else {
                    const err = await res.json();
                    alert(err.detail || 'Failed to send sealed contract');
                }
            } catch (err) {
                alert('Action failed due to connection error.');
            } finally {
                btn.innerText = 'Finalize & Send';
                btn.disabled = false;
            }
        }

        // --- LEGAL ARCHIVE ---
        async function fetchArchive() {
            try {
                const res = await fetch(`${API_BASE}/archive`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                if (res.ok) renderArchive(data);
                else console.error('Archive error:', data);
            } catch (err) { console.error('Archive load failed'); }
        }

        function renderArchive(data) {
            const tbody = document.getElementById('archiveTableBody');
            if (!tbody) return;
            if (!Array.isArray(data)) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-12 text-center text-red-500">Error loading archive. Please ensure database columns are synced.</td></tr>';
                return;
            }
            tbody.innerHTML = data.map(session => `
                <tr class="border-b border-[#2D2F36] hover:bg-white/5 transition">
                    <td class="px-6 py-4">
                        <p class="font-bold text-brand-gold">${session.invoices?.invoice_number || 'N/A'}</p>
                        <p class="text-[10px] text-gray-500 uppercase tracking-widest">v${session.id.slice(0, 4)}</p>
                    </td>
                    <td class="px-6 py-4">
                        <p class="text-sm text-gray-300 font-bold">${new Date(session.created_at).toLocaleDateString()}</p>
                    </td>
                    <td class="px-6 py-4">
                        <p class="text-sm font-bold text-white">${session.invoices?.clients?.full_name || 'N/A'}</p>
                    </td>
                    <td class="px-6 py-4 flex gap-2">
                        <button onclick="downloadDoc('${session.invoice_id}', 'contract')" class="bg-white/5 hover:bg-white/10 p-2 rounded text-gray-400" title="Download Contract">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                        </button>
                        <button onclick="downloadDoc('${session.invoice_id}', 'certificate')" class="bg-white/5 hover:bg-white/10 p-2 rounded text-brand-gold" title="Download Audit Certificate">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                        </button>
                    </td>
                </tr>
            `).join('');
            if (data.length === 0) tbody.innerHTML = '<tr><td colspan="4" class="p-12 text-center text-gray-500">No executed contracts found in archive.</td></tr>';
        }

        async function downloadDoc(invoiceId, type) {
            const url = type === 'contract' ? `/api/contracts/${invoiceId}/contract` : `/api/contracts/${invoiceId}/certificate`;
            const token = localStorage.getItem('ec_token');
            window.open(`${url}?token=${token}`, '_blank');
        }

        async function loadAuthorities() {
            try {
                const res = await fetch(`${API_BASE}/signatures`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                const data = await res.json();
                renderAuthorities(data);
            } catch (err) { console.error('Authority load error:', err); }
        }

        function checkAuth() {
            const token = localStorage.getItem('ec_token');
            const admin = JSON.parse(localStorage.getItem('admin') || '{}');
            const displayName = admin.full_name || admin.name || 'User';
            const allowedRoles = ['admin', 'super_admin', 'lawyer', 'legal'];
            const roles = (admin.role || '').toLowerCase().split(',').map(r => r.trim()).filter(Boolean);

            if (!token || !admin.role) {
                window.location.href = '/login';
                return;
            }

            if (!roles.some(role => allowedRoles.includes(role))) {
                alert('Access denied. You do not have permission to view this page.');
                window.location.href = '/dashboard';
                return;
            }

            document.getElementById('adminName').innerText = displayName;
            const _legalRoleLabels = { super_admin: '💎 Super Admin', admin: '⭐ Admin', lawyer: '⚖️ Lawyer', legal: '⚖️ Legal' };
            const _legalPrimaryRole = (admin.role || '').split(',')[0].trim();
            document.getElementById('adminRole').innerText = _legalRoleLabels[_legalPrimaryRole] || _legalPrimaryRole.replace(/_/g, ' ') || 'User';
            document.getElementById('adminInitial').innerText = displayName ? displayName[0].toUpperCase() : 'A';

            // Show Finance links ONLY for admins
            if (roles.includes('admin') || roles.includes('super_admin')) {
                const navFin = document.getElementById('nav-finance-container');
                const navFinSide = document.getElementById('nav-finance-container-sidebar');
                if (navFin) navFin.style.display = 'block';
                if (navFinSide) navFinSide.style.display = 'block';
            }
        }

        function logout() {
            localStorage.clear();
            window.location.href = '/login';
        }

        let hrStaff = [];
        async function fetchHRStaff() {
            try {
                const res = await fetch('/api/hr/staff', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                if (res.ok) {
                    hrStaff = await res.json();
                    const dl = document.getElementById('staff-search-results');
                    if (dl) {
                        dl.innerHTML = hrStaff.map(s =>
                            `<option value="${s.full_name}">${s.email} | ${s.department || 'No Dept'} | ${s.primary_role || ''}</option>`
                        ).join('');
                    }
                }
            } catch (err) { console.error('Failed to fetch HR directory'); }
        }

        function handleStaffSearch(val) {
            const found = hrStaff.find(s => s.full_name === val);
            if (found) {
                document.getElementById('initiate-party-email').value = found.email;
                document.getElementById('initiate-staff-id').value = found.id;
            } else {
                // If they changed it or it's external, clear the ID
                document.getElementById('initiate-staff-id').value = '';
            }
        }

        window.onload = () => {
            checkAuth();
            fetchSummary();
            fetchContracts();
            loadAuthorities();
            fetchArchive();
            fetchActivity();
            fetchExecutionTrends();
            fetchHRStaff();
            setInterval(fetchActivity, 60000);
            fetchNotifications(); // initial load
            setInterval(fetchNotifications, 120000); // poll every 2 min
        };

        // --- INITIATION LOGIC ---
        async function openInitiateModal(category) {
            if (category) {
                document.getElementById('initiate-category').value = category;
            }
            document.getElementById('initiateModal').classList.remove('hidden');

            // Populate the Assign Drafter dropdown from collaborator-candidates
            const drafterSelect = document.getElementById('initiate-drafter-id');
            drafterSelect.innerHTML = '<option value="">-- Myself (default) --</option>';
            try {
                const res = await fetch(`${HR_LEGAL_API}/collaborator-candidates`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                if (res.ok) {
                    const candidates = await res.json();
                    // Prioritise lawyers/legal roles at the top
                    const lawyers = candidates.filter(c => (c.role || '').toLowerCase().includes('legal') || (c.role || '').toLowerCase().includes('lawyer'));
                    const others = candidates.filter(c => !lawyers.includes(c));
                    const sorted = [...lawyers, ...others];
                    sorted.forEach(c => {
                        const opt = document.createElement('option');
                        opt.value = c.id;
                        opt.textContent = `${c.full_name} (${c.role || 'Admin'})`;
                        drafterSelect.appendChild(opt);
                    });
                }
            } catch (e) {
                console.warn('Could not load drafter candidates:', e);
            }
        }


        function closeInitiateModal() {
            document.getElementById('initiateModal').classList.add('hidden');
        }

        async function submitInitiate() {
            const btn = event.currentTarget;
            const originalText = btn.innerHTML;

            try {
                const category = document.getElementById('initiate-category').value;
                const title = document.getElementById('initiate-title').value;
                const partyName = document.getElementById('initiate-party-name').value;
                const partyEmail = document.getElementById('initiate-party-email').value;
                const staffId = document.getElementById('initiate-staff-id').value;

                if (!title) { alert('Please enter a matter title'); return; }

                btn.disabled = true;
                btn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Initializing...`;

                const payload = {
                    category: category,
                    title: title,
                    staff_id: staffId || null,
                    external_party_name: staffId ? null : partyName,
                    external_party_email: staffId ? null : partyEmail,
                    drafter_id: document.getElementById('initiate-drafter-id').value || null,
                    status: 'Draft'
                };

                console.log('Initiating matter with payload:', payload);

                const res = await fetch(`${HR_LEGAL_API}/matters`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
                    },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to create matter');
                }

                const matter = await res.json();
                console.log('Matter created:', matter);

                // Success! Redirect to editor
                window.location.href = `/legal/advanced-editor?id=${matter.id}`;
            } catch (err) {
                console.error('Initiation error:', err);
                alert(err.message || 'Connection error. Please check your network.');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }
    

        // ── AUDIT TRAIL ──
        async function openAuditTrail(matterId) {
            const modal = document.getElementById('auditModal');
            const titleEl = document.getElementById('audit-matter-title');
            const loadingEl = document.getElementById('audit-loading');
            const entriesEl = document.getElementById('audit-entries');
            const emptyEl = document.getElementById('audit-empty');
            const errorEl = document.getElementById('audit-error');

            // Reset state
            modal.classList.remove('hidden');
            document.body.classList.add('overflow-hidden');
            loadingEl.classList.remove('hidden');
            entriesEl.classList.add('hidden');
            emptyEl.classList.add('hidden');
            errorEl.classList.add('hidden');
            titleEl.textContent = 'Loading…';
            entriesEl.innerHTML = '';

            try {
                const res = await fetch(`/api/hr-legal/matters/${matterId}`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
                });
                if (!res.ok) throw new Error('Fetch failed');
                const data = await res.json();

                titleEl.textContent = data.matter?.title || matterId.split('-')[0] + '…';
                const history = data.history || [];

                loadingEl.classList.add('hidden');

                if (history.length === 0) {
                    emptyEl.classList.remove('hidden');
                    return;
                }

                const actionColors = {
                    'Created': 'text-green-400',
                    'Saved': 'text-blue-400',
                    'Status Changed': 'text-yellow-400',
                    'Collaborator Added': 'text-purple-400',
                    'Staff Viewed': 'text-cyan-400',
                    'Visibility Changed': 'text-orange-400',
                };
                const actionIcons = {
                    'Created': '🟢',
                    'Saved': '💾',
                    'Status Changed': '🔄',
                    'Collaborator Added': '👥',
                    'Staff Viewed': '👁️',
                    'Visibility Changed': '🔒',
                };

                entriesEl.innerHTML = history.map(h => {
                    const color = actionColors[h.action] || 'text-gray-300';
                    const icon = actionIcons[h.action] || '📋';
                    const date = new Date(h.created_at).toLocaleString();
                    return `
                        <div class="flex gap-4 items-start bg-white/3 border border-white/5 rounded-xl px-4 py-3 hover:bg-white/5 transition">
                            <span class="text-lg mt-0.5" style="flex-shrink:0">${icon}</span>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-3 flex-wrap">
                                    <span class="text-xs font-bold ${color}">${h.action}</span>
                                    <span class="text-[10px] text-gray-500">${date}</span>
                                </div>
                                ${h.description ? `<p class="text-[11px] text-gray-400 mt-1 leading-relaxed">${h.description}</p>` : ''}
                            </div>
                        </div>`;
                }).join('');

                entriesEl.classList.remove('hidden');

            } catch (err) {
                loadingEl.classList.add('hidden');
                errorEl.classList.remove('hidden');
                console.error('Audit trail error:', err);
            }
        }

        function closeAuditModal() {
            document.getElementById('auditModal').classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        }

        // Close on backdrop click
        document.getElementById('auditModal').addEventListener('click', function (e) {
            if (e.target === this) closeAuditModal();
        });
    

        /* ─── State ───────────────────────────────────────────────── */
        let _vaultMatterId = null;
        let _vaultMatterTitle = '';
        let _vaultShowAll = false;

        /* ─── Open / Close ────────────────────────────────────────── */
        function openVaultPanel(matterId, matterTitle) {
            console.log('Opening vault for:', matterId, matterTitle);
            _vaultMatterId = matterId;
            _vaultMatterTitle = matterTitle || matterId.split('-')[0] + '…';
            _vaultShowAll = false;

            document.getElementById('vaultMatterTitle').textContent = _vaultMatterTitle;
            document.getElementById('vaultMatterLabel').textContent = 'Document Hub — ' + matterId.split('-')[0].toUpperCase();
            document.getElementById('vaultVersionToggleIcon').textContent = '▼';
            document.getElementById('vaultVersionToggleLabel').textContent = ' Show all versions';

            const panel = document.getElementById('vaultPanel');
            const backdrop = document.getElementById('vaultBackdrop');

            if (panel) panel.classList.add('open');
            if (backdrop) backdrop.classList.add('open');

            document.body.style.overflow = 'hidden';
            loadVaultFiles();
        }

        function closeVaultPanel() {
            const panel = document.getElementById('vaultPanel');
            const backdrop = document.getElementById('vaultBackdrop');

            if (panel) panel.classList.remove('open');
            if (backdrop) backdrop.classList.remove('open');

            document.body.style.overflow = '';
            _vaultMatterId = null;
        }

        /* ─── Load Files ──────────────────────────────────────────── */
        async function loadVaultFiles() {
            if (!_vaultMatterId) return;
            const list = document.getElementById('vaultFileList');
            list.innerHTML = `
                    <div style="padding:60px 20px; text-align:center;">
                        <div class="vault-spinner"></div>
                        <div style="color:#9CA3AF; font-size:12px; font-weight:500; letter-spacing:0.05em; text-transform:uppercase;">Synchronizing Vault...</div>
                    </div>
                `;
            try {
                const url = HR_LEGAL_API + '/matters/' + _vaultMatterId + '/attachments?include_all=' + _vaultShowAll;
                const res = await fetch(url, {
                    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('ec_token') }
                });
                if (!res.ok) throw new Error(await res.text());
                const data = await res.json();
                renderVaultFiles(data.attachments || []);
            } catch (err) {
                list.innerHTML = '<div class="vault-empty"><span class="vault-empty-icon">⚠️</span><div class="vault-empty-text">Failed to load files.<br><small>' + err.message + '</small></div></div>';
            }
        }

        function renderVaultFiles(attachments) {
            const list = document.getElementById('vaultFileList');
            const count = document.getElementById('vaultFileCount');
            const active = attachments.filter(a => a.status === 'Active');
            count.textContent = active.length + ' file' + (active.length !== 1 ? 's' : '') + ' in vault';

            if (!attachments.length) {
                list.innerHTML = '<div class="vault-empty"><span class="vault-empty-icon">🗄️</span><div class="vault-empty-text">No documents uploaded yet.<br>Use the zone above to add the first file.</div></div>';
                return;
            }

            list.innerHTML = attachments.map(att => {
                const isLatest = att.is_latest;
                const isSuperseded = att.status === 'Superseded';
                const ext = att.file_type;
                const icon = ext === 'pdf' ? '📄' : '📝';
                const sizeMB = (att.file_size_bytes / 1048576).toFixed(2);
                const uploadedAt = new Date(att.uploaded_at).toLocaleDateString('en-GB', {
                    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                });

                const safeFilename = att.original_filename.replace(/'/g, "\\'");

                const dlBtn = `<button class="vault-btn" onclick="vaultDownload('${att.id}', '${safeFilename}')" title="Download">${att.signed_url ? '⬇' : '⬇'}</button>`;
                const previewBtn = (ext === 'pdf' && att.signed_url)
                    ? `<button class="vault-btn" onclick="vaultPreviewPDF('${att.signed_url}', '${safeFilename}')" title="Preview PDF">👁</button>`
                    : '';
                const delBtn = !isSuperseded
                    ? `<button class="vault-btn danger" onclick="vaultDelete('${att.id}', '${safeFilename}')" title="Remove from vault">🗑</button>`
                    : '';

                return `
                        <div class="vault-file-item" style="${isSuperseded ? 'opacity:0.48' : ''}">
                            <div class="vault-file-icon ${ext}">${icon}</div>
                            <div class="vault-file-meta">
                                <div class="vault-file-name" title="${att.original_filename}">${att.original_filename}</div>
                                <div class="vault-file-details">
                                    <span class="vault-version-badge ${isSuperseded ? 'superseded' : ''}">v${att.version_number} — ${att.version_label || 'Draft'}</span>
                                    <span>${sizeMB} MB</span>
                                    ${isLatest ? '<span style="color:#22c55e;font-weight:700;">● Latest</span>' : ''}
                                </div>
                                <div class="vault-file-uploader">⬆ ${att.uploader_name} &middot; ${uploadedAt}</div>
                            </div>
                            <div class="vault-file-actions">${dlBtn}${previewBtn}${delBtn}</div>
                        </div>`;
            }).join('');
        }

        /* ─── Version History Toggle ──────────────────────────────── */
        function toggleVersionHistory() {
            _vaultShowAll = !_vaultShowAll;
            document.getElementById('vaultVersionToggleIcon').textContent = _vaultShowAll ? '▲' : '▼';
            document.getElementById('vaultVersionToggleLabel').textContent = _vaultShowAll ? ' Hide old versions' : ' Show all versions';
            loadVaultFiles();
        }

        /* ─── Drag-and-Drop wiring ────────────────────────────────── */
        document.addEventListener('DOMContentLoaded', function () {
            const zone = document.getElementById('vaultDropZone');
            if (!zone) return;
            zone.addEventListener('dragover', function (e) {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.add('drag-over');
            });
            zone.addEventListener('dragleave', function (e) {
                e.stopPropagation();
                zone.classList.remove('drag-over');
            });
            zone.addEventListener('drop', function (e) {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.remove('drag-over');
                const droppedFile = e.dataTransfer.files[0];
                if (droppedFile) uploadVaultFile(droppedFile);
            });
        });

        function handleVaultFileSelect(input) {
            if (input.files && input.files[0]) {
                uploadVaultFile(input.files[0]);
                input.value = '';
            }
        }

        /* ─── Upload ──────────────────────────────────────────────── */
        async function uploadVaultFile(file) {
            if (!_vaultMatterId) return;

            // Validate by MIME type OR by file extension (browsers report inconsistent MIME for .doc)
            const ALLOWED_TYPES = [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/x-msword',
                'application/vnd.ms-word',
                'application/octet-stream'   // some OS report .doc/.docx this way
            ];
            const ALLOWED_EXTS = ['pdf', 'doc', 'docx'];
            const fileExt = (file.name.split('.').pop() || '').toLowerCase();

            if (!ALLOWED_TYPES.includes(file.type) && !ALLOWED_EXTS.includes(fileExt)) {
                showVaultToast('Only PDF, DOC, and DOCX files are allowed.', 'error'); return;
            }
            if (file.size > 20 * 1024 * 1024) {
                showVaultToast('File too large (' + (file.size / 1048576).toFixed(1) + ' MB). Max: 20 MB.', 'error'); return;
            }

            const progressBar = document.getElementById('vaultProgressBar');
            const progressFill = document.getElementById('vaultProgressFill');
            progressBar.style.display = 'block';
            progressFill.style.width = '0%';
            let pct = 0;
            const ticker = setInterval(function () {
                pct = Math.min(pct + Math.random() * 15, 85);
                progressFill.style.width = pct + '%';
            }, 200);

            try {
                const form = new FormData();
                form.append('file', file);
                const res = await fetch(HR_LEGAL_API + '/matters/' + _vaultMatterId + '/attachments', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('ec_token') },
                    body: form
                });
                const data = await res.json();
                clearInterval(ticker);
                progressFill.style.width = '100%';
                setTimeout(function () { progressBar.style.display = 'none'; progressFill.style.width = '0%'; }, 600);
                if (!res.ok) throw new Error(data.detail || 'Upload failed');
                showVaultToast('"' + file.name + '" uploaded to vault.', 'success');
                loadVaultFiles();
            } catch (err) {
                clearInterval(ticker);
                progressBar.style.display = 'none';
                showVaultToast('Upload failed: ' + err.message, 'error');
            }
        }

        /* ─── Download ────────────────────────────────────────────── */
        async function vaultDownload(attachmentId, filename) {
            try {
                const res = await fetch(HR_LEGAL_API + '/matters/' + _vaultMatterId + '/attachments/' + attachmentId + '/download', {
                    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('ec_token') }
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);
                const a = document.createElement('a');
                a.href = data.signed_url; a.download = filename; a.target = '_blank'; a.click();
            } catch (err) { showVaultToast('Download failed: ' + err.message, 'error'); }
        }

        /* ─── PDF Preview ─────────────────────────────────────────── */
        function vaultPreviewPDF(signedUrl, filename) {
            const overlay = document.createElement('div');
            overlay.className = 'vault-preview-overlay';
            overlay.innerHTML = '<div class="vault-preview-bar">'
                + '<span style="color:#fff;font-weight:600;font-size:14px;">📄 ' + filename + '</span>'
                + '<button onclick="this.closest(\'.vault-preview-overlay\').remove()" '
                + 'style="background:rgba(255,255,255,0.08);border:none;color:#fff;padding:6px 14px;border-radius:7px;cursor:pointer;font-size:13px;">✕ Close</button>'
                + '</div>'
                + '<iframe src="' + signedUrl + '" style="flex:1;border:none;width:100%;" title="Document Preview"></iframe>';
            document.body.appendChild(overlay);
        }

        /* ─── Delete ──────────────────────────────────────────────── */
        async function vaultDelete(attachmentId, filename) {
            if (!confirm('Remove "' + filename + '" from the vault?\n\nThis is logged in the audit trail.')) return;
            try {
                const res = await fetch(HR_LEGAL_API + '/matters/' + _vaultMatterId + '/attachments/' + attachmentId, {
                    method: 'DELETE',
                    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('ec_token') }
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);
                showVaultToast('File removed from vault.', 'success');
                loadVaultFiles();
            } catch (err) { showVaultToast('Delete failed: ' + err.message, 'error'); }
        }

        /* ─── Toast ───────────────────────────────────────────────── */

        // ═══════════════════════════════════════════════════════════
        //  NOTIFICATIONS SYSTEM
        // ═══════════════════════════════════════════════════════════
        window._allNotifications = [];
        const NOTIF_ICONS = {
            invite: '⚖️', contract: '📋', signing: '✍️', executed: '✅',
            visibility: '👁️', system: '🔔', memo: '💬', subscription: '📝', witness: '🖊️', collaborator: '🤝', default: '🔔'
        };
        const NOTIF_COLORS = {
            invite: '#8B5CF6', contract: '#D4AF37', signing: '#3B82F6',
            executed: '#10B981', visibility: '#EC4899', system: '#6B7280',
            memo: '#F59E0B', subscription: '#06B6D4', witness: '#F97316', collaborator: '#8B5CF6', default: '#6B7280'
        };

        async function fetchNotifications() {
            try {
                const token = localStorage.getItem('ec_token');
                const res = await fetch(`${HR_LEGAL_API}/notifications`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (!res.ok) { renderNotifications([]); return; }
                const data = await res.json();
                window._allNotifications = data || [];
                renderNotifications(window._allNotifications);
                updateNotifBadge(window._allNotifications.filter(n => !n.is_read).length);
                updateNotifStats(window._allNotifications);
            } catch (err) {
                console.error('Notifications fetch error:', err);
                renderNotifications([]);
            }
        }

        function updateNotifBadge(count) {
            // Delegate to the bell panel's unified badge updater (keeps all 3 badges in sync)
            if (typeof window.updateAllNotifBadges === 'function') {
                window.updateAllNotifBadges(count);
                return;
            }
            // Fallback: original behaviour for the nav-link badge only
            const badges = ['notif-badge-desktop'];
            badges.forEach(id => {
                const el = document.getElementById(id);
                if (!el) return;
                if (count > 0) {
                    el.textContent = count > 99 ? '99+' : count;
                    el.classList.remove('hidden');
                } else {
                    el.classList.add('hidden');
                }
            });
        }

        function updateNotifStats(notifs) {
            const unread = notifs.filter(n => !n.is_read).length;
            const invites = notifs.filter(n => n.type === 'invite').length;
            const contracts = notifs.filter(n => n.type === 'contract' || n.type === 'visibility').length;
            const signing = notifs.filter(n => n.type === 'signing' || n.type === 'executed').length;
            const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
            el('notifStatUnread', unread);
            el('notifStatInvites', invites);
            el('notifStatContracts', contracts);
            el('notifStatSigning', signing);
        }

        function filterNotifications() {
            const filter = document.getElementById('notif-filter')?.value || 'all';
            if (filter === 'all') return renderNotifications(window._allNotifications);
            if (filter === 'unread') return renderNotifications(window._allNotifications.filter(n => !n.is_read));
            return renderNotifications(window._allNotifications.filter(n => n.type === filter));
        }

        function renderNotifications(notifs) {
            const container = document.getElementById('notif-list');
            if (!container) return;
            if (!notifs || notifs.length === 0) {
                container.innerHTML = `<div style="padding:60px;text-align:center;color:#6B7280;">
                    <div style="font-size:42px;margin-bottom:12px;">🔔</div>
                    <div style="font-size:14px;font-weight:700;margin-bottom:6px;">No notifications</div>
                    <div style="font-size:12px;">You're all caught up.</div>
                </div>`;
                return;
            }
            container.innerHTML = notifs.map(n => {
                const icon = NOTIF_ICONS[n.type] || NOTIF_ICONS.default;
                const color = NOTIF_COLORS[n.type] || NOTIF_COLORS.default;
                const ts = n.created_at ? new Date(n.created_at).toLocaleString() : '';
                const unreadStyle = !n.is_read ? 'border-left: 3px solid ' + color + ';' : '';
                const bgStyle = !n.is_read ? 'background: ' + color + '08;' : '';
                return `<div class="notif-item" id="notif-${n.id}" style="${bgStyle}${unreadStyle}padding:18px 24px;cursor:pointer;transition:background 0.2s;"
                    onmouseenter="this.style.background='${color}12'"
                    onmouseleave="this.style.background='${!n.is_read ? color + '08' : 'transparent'}'"
                    onclick="handleNotifClick(${JSON.stringify(n).replace(/"/g, '&quot;')})">
                    <div style="display:flex;gap:14px;align-items:flex-start;">
                        <div style="width:40px;height:40px;border-radius:50%;background:${color}20;border:1px solid ${color}33;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">${icon}</div>
                        <div style="flex:1;min-width:0;">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:4px;">
                                <div style="font-size:13px;font-weight:${!n.is_read ? '800' : '600'};color:${!n.is_read ? '#F9FAFB' : '#9CA3AF'};line-height:1.3;">${n.title || 'Notification'}</div>
                                <div style="display:flex;gap:6px;align-items:center;flex-shrink:0;">
                                    ${!n.is_read ? `<span style="width:7px;height:7px;border-radius:50%;background:${color};display:inline-block;"></span>` : ''}
                                    <span style="font-size:10px;color:#6B7280;white-space:nowrap;">${ts}</span>
                                </div>
                            </div>
                            <div style="font-size:12px;color:#9CA3AF;line-height:1.5;margin-bottom:8px;">${n.message || ''}</div>
                            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                                <span style="font-size:9px;font-weight:800;background:${color}18;color:${color};border:1px solid ${color}30;border-radius:5px;padding:2px 7px;text-transform:uppercase;letter-spacing:0.5px;">${n.type || 'system'}</span>
                                ${n.matter_id ? `<button onclick="event.stopPropagation();openMatterFromNotif('${n.matter_id}')" style="font-size:9px;font-weight:700;background:#ffffff08;border:1px solid #2D2F36;color:#9CA3AF;border-radius:5px;padding:2px 9px;cursor:pointer;">Open Contract →</button>` : ''}
                                ${!n.is_read ? `<button onclick="event.stopPropagation();markNotifRead('${n.id}')" style="font-size:9px;font-weight:700;background:#ffffff08;border:1px solid #2D2F36;color:#9CA3AF;border-radius:5px;padding:2px 9px;cursor:pointer;">Mark Read</button>` : ''}
                            </div>
                        </div>
                    </div>
                </div>`;
            }).join('');
        }

        async function handleNotifClick(n) {
            if (!n.is_read) await markNotifRead(n.id);
            if (n.matter_id) openMatterFromNotif(n.matter_id);
        }

        function openMatterFromNotif(matterId) {
            window.open(`/legal/view?id=${matterId}`, '_blank');
        }

        async function markNotifRead(notifId) {
            try {
                const token = localStorage.getItem('ec_token');
                await fetch(`${HR_LEGAL_API}/notifications/${notifId}/read`, {
                    method: 'PATCH', headers: { 'Authorization': `Bearer ${token}` }
                });
                window._allNotifications = window._allNotifications.map(n => n.id === notifId ? { ...n, is_read: true } : n);
                filterNotifications();
                updateNotifBadge(window._allNotifications.filter(n => !n.is_read).length);
                updateNotifStats(window._allNotifications);
            } catch (err) { console.error('Mark read error:', err); }
        }

        async function markAllNotifRead() {
            try {
                const token = localStorage.getItem('ec_token');
                await fetch(`${HR_LEGAL_API}/notifications/read-all`, {
                    method: 'PATCH', headers: { 'Authorization': `Bearer ${token}` }
                });
                window._allNotifications = window._allNotifications.map(n => ({ ...n, is_read: true }));
                filterNotifications();
                updateNotifBadge(0);
                updateNotifStats(window._allNotifications);
            } catch (err) { console.error('Mark all read error:', err); }
        }

        let _vaultToastTimer = null;
        function showVaultToast(msg, type) {
            type = type || 'success';
            const toast = document.getElementById('vaultToast');
            document.getElementById('vaultToastMsg').textContent = msg;
            document.getElementById('vaultToastIcon').textContent = type === 'success' ? '✅' : '❌';
            toast.className = 'vault-toast show ' + type;
            clearTimeout(_vaultToastTimer);
            _vaultToastTimer = setTimeout(function () { toast.classList.remove('show'); }, 3500);
        }
    
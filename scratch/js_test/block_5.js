
        (function () {
            'use strict';

            // ── icon / colour maps ────────────────────────────────────
            var ICONS = {
                invite: '⚖️', contract: '📋', signing: '✍️',
                executed: '✅', visibility: '👁️', memo: '💬',
                system: '🔔', subscription: '📝', witness: '🖊️',
                collaborator: '🤝'
            };
            var COLORS = {
                invite: '#8B5CF6', contract: '#D4AF37', signing: '#3B82F6',
                executed: '#10B981', visibility: '#EC4899', memo: '#F59E0B',
                system: '#6B7280', subscription: '#06B6D4', witness: '#F97316',
                collaborator: '#8B5CF6'
            };
            var DEFAULT_ICON = '🔔';
            var DEFAULT_COLOR = '#6B7280';

            // ── helpers ───────────────────────────────────────────────
            function escHtml(s) {
                if (!s) return '';
                return String(s)
                    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
            }

            function timeAgo(date) {
                var secs = Math.floor((Date.now() - date) / 1000);
                if (secs < 60) return 'just now';
                if (secs < 3600) return Math.floor(secs / 60) + 'm ago';
                if (secs < 86400) return Math.floor(secs / 3600) + 'h ago';
                return Math.floor(secs / 86400) + 'd ago';
            }

            function getApiBase() {
                return (typeof window.HR_LEGAL_API !== 'undefined') ? window.HR_LEGAL_API : '/api/hr-legal';
            }

            function getToken() { return localStorage.getItem('ec_token') || ''; }

            // ── badge sync ────────────────────────────────────────────
            function syncBadges(count) {
                ['notif-badge-mobile', 'notif-badge-sidebar', 'notif-badge-desktop'].forEach(function (id) {
                    var el = document.getElementById(id);
                    if (!el) return;
                    if (count > 0) {
                        el.textContent = count > 99 ? '99+' : count;
                        el.style.display = 'inline-flex';
                        el.classList.remove('hidden');
                    } else {
                        el.style.display = 'none';
                        el.classList.add('hidden');
                    }
                });
            }
            window.updateAllNotifBadges = syncBadges;

            // ── local snapshot for click handler ─────────────────────
            var _panelNotifs = [];

            // ── render panel list ─────────────────────────────────────
            function renderPanel() {
                var list = document.getElementById('notif-panel-list');
                var sub  = document.getElementById('notif-panel-subtitle');
                if (!list || !sub) return;

                var all    = window._allNotifications || [];
                var notifs = all.slice(0, 8);
                _panelNotifs = notifs;

                var unread = all.filter(function (n) { return !n.is_read; }).length;
                sub.textContent = unread > 0 ? (unread + ' unread') : 'All caught up';

                if (!notifs.length) {
                    list.innerHTML = '<div style="padding:48px 24px;text-align:center;color:#6B7280;">'
                        + '<div style="font-size:36px;margin-bottom:10px;">⚖️</div>'
                        + '<div style="font-size:13px;font-weight:700;color:#9CA3AF;margin-bottom:4px;">No legal alerts yet</div>'
                        + '<div style="font-size:11px;">You\'ll be notified about contracts,<br>signatures, and collaborations here.</div>'
                        + '</div>';
                    return;
                }

                list.innerHTML = notifs.map(function (n, idx) {
                    var icon   = ICONS[n.type]  || DEFAULT_ICON;
                    var color  = COLORS[n.type] || DEFAULT_COLOR;
                    var ts     = n.created_at ? timeAgo(new Date(n.created_at)) : '';
                    var border = !n.is_read ? 'border-left:3px solid ' + color + ';' : 'border-left:3px solid transparent;';
                    var bg     = !n.is_read ? 'background:' + color + '0D;' : '';
                    var dot    = !n.is_read ? '<span style="width:6px;height:6px;border-radius:50%;background:' + color + ';flex-shrink:0;margin-top:4px;display:inline-block;"></span>' : '';
                    var fw     = !n.is_read ? '800' : '600';
                    var tc     = !n.is_read ? '#F9FAFB' : '#9CA3AF';

                    return '<div style="' + bg + border + 'padding:14px 18px;cursor:pointer;display:flex;gap:12px;align-items:flex-start;" '
                        + 'onclick="window._notifClick(' + idx + ')">'
                        + '<div style="width:34px;height:34px;flex-shrink:0;border-radius:50%;background:' + color + '1A;border:1px solid ' + color + '33;display:flex;align-items:center;justify-content:center;font-size:15px;">' + icon + '</div>'
                        + '<div style="flex:1;min-width:0;">'
                        +   '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;margin-bottom:2px;">'
                        +     '<div style="font-size:12px;font-weight:' + fw + ';color:' + tc + ';line-height:1.3;flex:1;">' + escHtml(n.title || 'Notification') + '</div>'
                        +     dot
                        +   '</div>'
                        +   '<div style="font-size:11px;color:#6B7280;line-height:1.45;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(n.message || '') + '</div>'
                        +   '<div style="display:flex;gap:6px;align-items:center;">'
                        +     '<span style="font-size:8px;font-weight:800;background:' + color + '18;color:' + color + ';border:1px solid ' + color + '30;border-radius:4px;padding:1px 6px;text-transform:uppercase;">' + escHtml(n.type || 'system') + '</span>'
                        +     '<span style="font-size:10px;color:#4B5563;">' + ts + '</span>'
                        +   '</div>'
                        + '</div></div>';
                }).join('<div style="height:1px;background:rgba(255,255,255,0.04);margin:0 18px;"></div>');
            }

            // ── fetch on demand then render ───────────────────────────
            function fetchAndRender() {
                if (window._allNotifications && window._allNotifications.length > 0) {
                    renderPanel();
                    return;
                }
                var list = document.getElementById('notif-panel-list');
                if (list) {
                    list.innerHTML = '<div style="padding:40px 24px;text-align:center;color:#6B7280;font-size:12px;">'
                        + '<div style="font-size:28px;margin-bottom:8px;">🔔</div>Loading…</div>';
                }
                fetch(getApiBase() + '/notifications', {
                    headers: { 'Authorization': 'Bearer ' + getToken() }
                }).then(function (res) {
                    return res.ok ? res.json() : [];
                }).then(function (data) {
                    window._allNotifications = data || [];
                    syncBadges(window._allNotifications.filter(function (n) { return !n.is_read; }).length);
                    renderPanel();
                }).catch(function () { renderPanel(); });
            }

            // ── open / close ──────────────────────────────────────────
            function openPanel(e) {
                var panel   = document.getElementById('notif-panel');
                var overlay = document.getElementById('notif-panel-overlay');
                if (!panel || !overlay) { console.warn('[Notif] panel element not found'); return; }

                var vw = window.innerWidth;
                panel.style.top   = 'auto';
                panel.style.left  = 'auto';
                panel.style.right = 'auto';

                if (vw <= 1024) {
                    panel.style.top   = '70px';
                    panel.style.right = '12px';
                } else {
                    var SIDEBAR_W = 260, PANEL_W = 360, GAP = 8;
                    var leftPx = Math.min(SIDEBAR_W + GAP, vw - PANEL_W - 8);
                    if (leftPx < 8) leftPx = 8;
                    var btn  = (e && e.currentTarget) || document.getElementById('notif-bell-desktop');
                    var rect = btn ? btn.getBoundingClientRect() : null;
                    panel.style.top  = (rect && rect.bottom ? Math.max(8, rect.bottom) : 80) + 'px';
                    panel.style.left = leftPx + 'px';
                }

                panel.style.zIndex   = '999999';
                overlay.style.zIndex = '999998';
                panel.style.display   = 'block';
                overlay.style.display = 'block';
                fetchAndRender();
            }

            function closePanel() {
                var panel   = document.getElementById('notif-panel');
                var overlay = document.getElementById('notif-panel-overlay');
                if (panel)   panel.style.display   = 'none';
                if (overlay) overlay.style.display = 'none';
            }

            // ── public window API ─────────────────────────────────────
            window.toggleNotifPanel = function (e) {
                if (e && e.stopPropagation) e.stopPropagation();
                var panel = document.getElementById('notif-panel');
                if (!panel) { console.warn('[Notif] #notif-panel not found'); return; }
                if (panel.style.display === 'block') { closePanel(); } else { openPanel(e); }
            };

            window.closeNotifPanel = closePanel;

            window._notifClick = function (idx) {
                var n = _panelNotifs[idx];
                if (!n) return;
                closePanel();
                if (!n.is_read && window._allNotifications) {
                    window._allNotifications = window._allNotifications.map(function (x) {
                        return x.id === n.id ? Object.assign({}, x, { is_read: true }) : x;
                    });
                    syncBadges(window._allNotifications.filter(function (x) { return !x.is_read; }).length);
                    fetch(getApiBase() + '/notifications/' + n.id + '/read', {
                        method: 'PATCH', headers: { 'Authorization': 'Bearer ' + getToken() }
                    }).catch(function () {});
                }
                if (n.matter_id) {
                    window.open('/legal/view?id=' + n.matter_id, '_blank');
                } else if (typeof switchTab === 'function') {
                    switchTab('notifications');
                }
            };

            window.panelMarkAllRead = function () {
                fetch(getApiBase() + '/notifications/read-all', {
                    method: 'PATCH', headers: { 'Authorization': 'Bearer ' + getToken() }
                }).then(function () {
                    if (window._allNotifications) {
                        window._allNotifications = window._allNotifications.map(function (n) {
                            return Object.assign({}, n, { is_read: true });
                        });
                    }
                    syncBadges(0);
                    renderPanel();
                    if (typeof filterNotifications === 'function') filterNotifications();
                    if (typeof updateNotifStats === 'function') updateNotifStats(window._allNotifications || []);
                }).catch(function (err) { console.error('[Notif] mark-all-read error:', err); });
            };

            // ── close on Escape ───────────────────────────────────────
            document.addEventListener('keydown', function (k) {
                if (k.key === 'Escape') closePanel();
            });

            // ── wrap existing fetchNotifications to sync badges ───────
            var _origFetch = window.fetchNotifications;
            if (typeof _origFetch === 'function') {
                window.fetchNotifications = function () {
                    var r = _origFetch.apply(this, arguments);
                    Promise.resolve(r).then(function () {
                        syncBadges((window._allNotifications || []).filter(function (n) { return !n.is_read; }).length);
                    });
                    return r;
                };
            }
        })();
    
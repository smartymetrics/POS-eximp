
        // Bottom nav active state sync
        function updateBottomNav(tabId) {
            ['dashboard', 'execution-portal', 'signature-vault', 'archive'].forEach(id => {
                const btn = document.getElementById(`bnav-${id}`);
                if (!btn) return;
                if (id === tabId) {
                    btn.classList.add('text-brand-gold');
                    btn.classList.remove('text-gray-500');
                } else {
                    btn.classList.remove('text-brand-gold');
                    btn.classList.add('text-gray-500');
                }
            });
        }

        // Give content breathing room above bottom bar on mobile
        (function () {
            const style = document.createElement('style');
            style.textContent = '@media (max-width:768px) { .main-content { padding-bottom: 80px !important; } }';
            document.head.appendChild(style);
        })();
    
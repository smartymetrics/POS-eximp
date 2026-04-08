/**
 * Eximp & Cloves - Deep Site Tracking (Industrial Grade)
 * ---------------------------------------------------
 * This script tracks visitor behavior on the property listings website
 * and links it back to the Marketing Dashboard contacts.
 */

(function() {
    const API_BASE = "https://app.eximps-cloves.com"; 
    const CONTACT_KEY = "ec_cid";
    const CAMPAIGN_KEY = "mcid"; // Marketing Campaign ID
    const UTM_PARAMS = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];

    // 1. Capture IDs & UTMs from URL
    const urlParams = new URLSearchParams(window.location.search);
    
    // Capture Contact ID
    const cidFromUrl = urlParams.get(CONTACT_KEY);
    if (cidFromUrl) {
        localStorage.setItem(CONTACT_KEY, cidFromUrl);
        console.log("Eximp Tracker: Contact linked:", cidFromUrl);
    }

    // Capture Marketing Campaign ID (mcid)
    const mcidFromUrl = urlParams.get(CAMPAIGN_KEY);
    if (mcidFromUrl) {
        localStorage.setItem(CAMPAIGN_KEY, mcidFromUrl);
        console.log("Eximp Tracker: Campaign linked:", mcidFromUrl);
    }

    // Capture UTMs for rich analytics
    UTM_PARAMS.forEach(param => {
        const val = urlParams.get(param);
        if (val) {
            localStorage.setItem(`ec_${param}`, val);
        }
    });

    const cid = localStorage.getItem(CONTACT_KEY);
    if (!cid) return; // Anonymous visitor, no CRM link

    // 2. Track Page View
    let lastUrl = window.location.href;

    async function trackView() {
        const payload = {
            contact_id: cid,
            url: window.location.href,
            title: document.title,
            referrer: document.referrer,
            timestamp: new Date().toISOString()
        };

        try {
            await fetch(`${API_BASE}/api/marketing/track`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } catch (e) {
            console.error("Eximp Tracker Error:", e);
        }
    }

    // 3. SPA Support: Listen for URL changes (React Router)
    const handleUrlChange = () => {
        const currentUrl = window.location.href;
        if (currentUrl !== lastUrl) {
            lastUrl = currentUrl;
            trackView();
        }
    };

    // Monkey-patch history methods
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = function(...args) {
        originalPushState.apply(this, args);
        handleUrlChange();
    };

    history.replaceState = function(...args) {
        originalReplaceState.apply(this, args);
        handleUrlChange();
    };

    window.addEventListener('popstate', handleUrlChange);

    // Initial run
    if (document.readyState === 'complete') {
        trackView();
    } else {
        window.addEventListener('load', trackView);
    }

})();

/**
 * CLAUDE HUB - Configuration
 * Change port here if backend runs on a different port
 */

const CONFIG = {
    // Backend port - change this if your server runs elsewhere
    PORT: 8767,

    // Computed URLs. Use the current host so LAN/mobile access works.
    get API_URL() {
        const protocol = window.location.protocol || 'http:';
        const hostname = window.location.hostname || 'localhost';
        return `${protocol}//${hostname}:${this.PORT}`;
    },
    get WS_URL() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const hostname = window.location.hostname || 'localhost';
        return `${protocol}//${hostname}:${this.PORT}`;
    }
};

// Allow override from localStorage for quick testing
(function() {
    const savedPort = localStorage.getItem('claude-hub-port');
    if (savedPort && !isNaN(parseInt(savedPort))) {
        CONFIG.PORT = parseInt(savedPort);
        console.log(`[Config] Using custom port from localStorage: ${CONFIG.PORT}`);
    }
})();

// Helper to change port on the fly (run in console: setPort(8767))
window.setPort = function(port) {
    localStorage.setItem('claude-hub-port', port);
    console.log(`Port set to ${port}. Refresh to apply.`);
    if (confirm(`Port changed to ${port}. Reload now?`)) {
        location.reload();
    }
};

window.getCaptainName = function() {
    const name = window.CAPTAIN_NAME || localStorage.getItem('claude-hub-captain-name') || 'Captain';
    return name.trim() || 'Captain';
};

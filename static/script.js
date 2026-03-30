// Shared helper functions for all pages

function showMessage(elementId, msg, type) {
    const el = document.getElementById(elementId);
    if(el) {
        el.textContent = msg;
        el.className = `alert ${type}`;
        el.classList.remove('hidden');
    }
}

// Auto-connect WebSocket helper (if needed per page)
function createWebSocket(url, onMessage, onOpen, onClose) {
    const ws = new WebSocket(url);
    ws.onopen = onOpen || (() => console.log('WS connected'));
    ws.onmessage = (e) => onMessage(JSON.parse(e.data));
    ws.onclose = onClose || (() => console.log('WS closed'));
    ws.onerror = (e) => console.error('WS error', e);
    return ws;
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

// Format time remaining
function formatTimeRemaining(seconds) {
    if(seconds < 0) return "Ended";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
}
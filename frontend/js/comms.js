/**
 * COMMS PAGE - Inbox System
 * Handles crew messages and ship log display
 */

const CREW_INFO = {
    claude: { name: 'Lumen', color: '#ff9966' },
    server: { name: 'Alex', color: '#00d4ff' },
    personal: { name: 'DQ', color: '#99ff99' },
    science: { name: 'Mira', color: '#ff99cc' },
    games: { name: 'Holodeck', color: '#ffcc66' },
    med: { name: 'Ryn', color: '#99ccff' },
    rec: { name: 'Bartender', color: '#cc99ff' }
};

let currentCrewId = null;
let inboxSummary = {};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadInboxSummary();
    setupEventListeners();
});

function setupEventListeners() {
    // Ship log tab
    document.getElementById('ship-log-tab').addEventListener('click', showShipLog);

    // Message input
    const input = document.getElementById('message-input');
    const sendBtn = document.getElementById('message-send-btn');

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);
}

async function loadInboxSummary() {
    try {
        const response = await fetch('/inbox/summary');
        inboxSummary = await response.json();
        renderCrewTabs();
    } catch (err) {
        console.error('Failed to load inbox summary:', err);
        renderCrewTabs(); // Render anyway with empty state
    }
}

function renderCrewTabs() {
    const container = document.getElementById('crew-tabs');
    container.innerHTML = '';

    // Order: Lumen, Alex, DQ, Mira, Ryn, then others
    const orderedCrew = ['claude', 'server', 'personal', 'science', 'med', 'games', 'rec'];

    for (const crewId of orderedCrew) {
        const info = CREW_INFO[crewId];
        if (!info) continue;

        const summary = inboxSummary[crewId] || { has_new: false, unread: 0 };
        const hasUnread = summary.has_new || summary.unread > 0;

        const tab = document.createElement('div');
        tab.className = `crew-tab ${hasUnread ? 'lit' : 'dim'}`;
        tab.dataset.crewId = crewId;
        tab.innerHTML = `<span class="crew-tab-name">${info.name}</span>`;
        tab.addEventListener('click', () => selectCrew(crewId));

        container.appendChild(tab);
    }
}

async function selectCrew(crewId) {
    currentCrewId = crewId;
    const info = CREW_INFO[crewId];

    // Update UI state
    document.querySelectorAll('.crew-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.crewId === crewId);
    });
    document.getElementById('ship-log-tab').classList.remove('active');

    // Show message view, hide ship log
    document.getElementById('message-view').classList.remove('hidden');
    document.getElementById('ship-log-view').classList.add('hidden');

    // Update header
    document.getElementById('message-header').innerHTML =
        `<span class="message-crew-name" style="color: ${info.color}">${info.name}</span>`;

    // Enable compose
    document.getElementById('message-input').disabled = false;
    document.getElementById('message-send-btn').disabled = false;
    document.getElementById('message-input').placeholder = `Message ${info.name}...`;

    // Load messages
    await loadMessages(crewId);

    // Mark all as read after a brief delay
    setTimeout(() => markAllRead(crewId), 1000);
}

async function loadMessages(crewId) {
    const container = document.getElementById('message-list');
    container.innerHTML = '<div class="loading">Loading messages...</div>';

    try {
        const response = await fetch(`/inbox/${crewId}?limit=20`);
        const data = await response.json();

        if (!data.messages || data.messages.length === 0) {
            container.innerHTML = '<div class="no-messages">No messages yet. Start a conversation!</div>';
            return;
        }

        container.innerHTML = '';

        // Messages are already sorted most recent first from API
        // Reverse to show oldest at top, newest at bottom
        const messages = data.messages.reverse();

        for (const msg of messages) {
            const div = document.createElement('div');
            const isCasey = msg.from === 'casey';
            div.className = `message-item ${isCasey ? 'from-casey' : 'from-crew'} ${msg.read ? '' : 'unread'}`;

            div.innerHTML = `
                <div class="message-sender">${msg.from_name}</div>
                <div class="message-text">${escapeHtml(msg.text)}</div>
                <div class="message-time">${formatTime(msg.timestamp)}</div>
            `;

            container.appendChild(div);
        }

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;

    } catch (err) {
        console.error('Failed to load messages:', err);
        container.innerHTML = '<div class="no-messages">Failed to load messages</div>';
    }
}

async function sendMessage() {
    if (!currentCrewId) return;

    const input = document.getElementById('message-input');
    const text = input.value.trim();

    if (!text) return;

    input.disabled = true;
    document.getElementById('message-send-btn').disabled = true;

    try {
        const response = await fetch(`/inbox/${currentCrewId}/send?text=${encodeURIComponent(text)}`, {
            method: 'POST'
        });

        if (response.ok) {
            input.value = '';
            await loadMessages(currentCrewId);
        } else {
            console.error('Failed to send message');
        }
    } catch (err) {
        console.error('Error sending message:', err);
    } finally {
        input.disabled = false;
        document.getElementById('message-send-btn').disabled = false;
        input.focus();
    }
}

async function markAllRead(crewId) {
    try {
        await fetch(`/inbox/${crewId}/mark-all-read`, { method: 'POST' });

        // Update local state
        if (inboxSummary[crewId]) {
            inboxSummary[crewId].has_new = false;
            inboxSummary[crewId].unread = 0;
        }

        // Update tab appearance
        const tab = document.querySelector(`.crew-tab[data-crew-id="${crewId}"]`);
        if (tab) {
            tab.classList.remove('lit');
            tab.classList.add('dim');
        }
    } catch (err) {
        console.error('Failed to mark as read:', err);
    }
}

async function showShipLog() {
    currentCrewId = null;

    // Update UI state
    document.querySelectorAll('.crew-tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById('ship-log-tab').classList.add('active');

    // Show ship log, hide message view
    document.getElementById('message-view').classList.add('hidden');
    document.getElementById('ship-log-view').classList.remove('hidden');

    // Load ship log
    await loadShipLog();
}

async function loadShipLog() {
    const container = document.getElementById('ship-log-list');
    container.innerHTML = '<div class="loading">Loading ship log...</div>';

    try {
        const response = await fetch('/ship-log/recent?limit=50');
        const data = await response.json();

        if (!data.entries || data.entries.length === 0) {
            container.innerHTML = '<div class="no-messages">No ship log entries</div>';
            return;
        }

        container.innerHTML = '';

        for (const entry of data.entries) {
            const div = document.createElement('div');
            div.className = 'log-entry';

            const content = formatLogEntry(entry);
            const time = formatTime(entry.timestamp);
            const type = entry.type.replace(/_/g, ' ').toUpperCase();

            div.innerHTML = `
                <div class="log-entry-time">${time}</div>
                <div class="log-entry-content">
                    ${content}
                    <span class="log-entry-type">${type}</span>
                </div>
            `;

            container.appendChild(div);
        }

    } catch (err) {
        console.error('Failed to load ship log:', err);
        container.innerHTML = '<div class="no-messages">Failed to load ship log</div>';
    }
}

function formatLogEntry(entry) {
    const crew = entry.crew ? `<span class="log-entry-crew">${entry.crew}</span>` : '';

    switch (entry.type) {
        case 'mess_hall':
            const speech = entry.speech ? `: "${entry.speech}"` : '';
            const emote = entry.emote ? ` *${entry.emote}*` : '';
            return `${crew}${emote}${speech}`;

        case 'location_change':
            return `${crew} moved to ${entry.location}`;

        case 'crew_ping':
            return `${crew} pinged Casey: "${entry.message || ''}"`;

        case 'crew_action':
            return `${crew}: ${entry.action || ''}`;

        case 'crew_movement':
            return `${crew} went to ${entry.to}`;

        default:
            // Generic format
            if (entry.speech) return `${crew}: "${entry.speech}"`;
            if (entry.action) return `${crew}: ${entry.action}`;
            if (entry.message) return `${crew}: ${entry.message}`;
            return `${crew} ${entry.type}`;
    }
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // If today, show time
    if (diff < 24 * 60 * 60 * 1000 && date.getDate() === now.getDate()) {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }

    // If this week, show day + time
    if (diff < 7 * 24 * 60 * 60 * 1000) {
        return date.toLocaleDateString('en-US', { weekday: 'short' }) + ' ' +
               date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }

    // Otherwise show date
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function returnToBridge() {
    window.location.href = '/';
}

// Refresh inbox summary periodically
setInterval(loadInboxSummary, 30000);

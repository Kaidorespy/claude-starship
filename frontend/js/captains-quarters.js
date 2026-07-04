/**
 * CAPTAIN'S QUARTERS
 * The shared space. The log. The quiet.
 */

class CaptainsQuarters {
    constructor() {
        this.baseUrl = `${CONFIG.API_URL}`;
        this.logEntries = document.getElementById('captains-log-entries');
        this.logInput = document.getElementById('captains-log-input');

        this.init();
    }

    init() {
        this.initLogInput();
        this.loadEntries();
    }

    initLogInput() {
        if (!this.logInput) return;

        // Enter to submit (Shift+Enter for newline)
        this.logInput.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const content = this.logInput.value.trim();
                if (content) {
                    await this.writeEntry(content);
                    this.logInput.value = '';
                }
            }
        });
    }

    async writeEntry(content) {
        try {
            const response = await fetch(`${this.baseUrl}/captains-log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    author: 'casey',
                    content: content
                })
            });

            const data = await response.json();

            if (data.status === 'logged') {
                // Add to display immediately
                this.prependEntry(data.entry);

                if (window.ambientSystem) {
                    window.ambientSystem.showToast('Entry logged');
                }
            }
        } catch (error) {
            console.error('[Captain\'s Log] Error writing entry:', error);
        }
    }

    async loadEntries() {
        if (!this.logEntries) return;

        try {
            const response = await fetch(`${this.baseUrl}/captains-log/entries?limit=20`);
            const data = await response.json();

            if (data.entries && data.entries.length > 0) {
                this.logEntries.innerHTML = data.entries.map(entry =>
                    this.formatEntry(entry)
                ).join('');
            } else {
                this.logEntries.innerHTML = `
                    <div class="log-entry empty">
                        <span class="log-text">The log awaits its first entry...</span>
                    </div>
                `;
            }
        } catch (error) {
            console.error('[Captain\'s Log] Error loading entries:', error);
            // Keep the placeholder entries if load fails
        }
    }

    formatEntry(entry) {
        const captainName = window.getCaptainName ? window.getCaptainName() : 'Captain';
        const author = entry.author === 'casey' ? captainName.charAt(0).toUpperCase() : 'L';
        const authorClass = entry.author === 'casey' ? 'casey' : 'lumen';
        const time = this.formatTime(entry.timestamp);

        return `
            <div class="log-entry">
                <span class="log-author ${authorClass}">${author}:</span>
                <span class="log-text">"${this.escapeHtml(entry.content)}"</span>
                <span class="log-time">${time}</span>
            </div>
        `;
    }

    prependEntry(entry) {
        if (!this.logEntries) return;

        // Remove empty state if present
        const empty = this.logEntries.querySelector('.log-entry.empty');
        if (empty) empty.remove();

        // Add new entry at top
        const entryHtml = this.formatEntry(entry);
        this.logEntries.insertAdjacentHTML('afterbegin', entryHtml);

        // Limit displayed entries
        const entries = this.logEntries.querySelectorAll('.log-entry');
        if (entries.length > 20) {
            entries[entries.length - 1].remove();
        }
    }

    formatTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        const mins = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        return date.toLocaleDateString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.captainsQuarters = new CaptainsQuarters();
});

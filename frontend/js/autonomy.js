/**
 * AUTONOMY UI
 * Shows crew pings, activity, and ship life
 *
 * The ship is alive. Crew do things. This shows you what's happening.
 */

class AutonomyUI {
    constructor() {
        this.baseUrl = typeof CONFIG !== 'undefined' ? CONFIG.API_URL : `${CONFIG.API_URL}`;
        this.pings = [];
        this.moments = [];
        this.activityLog = [];
        this.notificationsEnabled = false;
        this.currentPing = null;
        this.pingEventSource = null;  // SSE connection for real-time pings
        this.captainStatus = 'here';  // 'here' or 'away'

        // Multiple walkies support - one per crew
        this.walkies = new Map();  // crewId -> { element, ws, ping }
        this.walkieOffsets = 0;    // For stacking walkies

        this.init();
    }

    init() {
        this.createPingBanner();
        this.createActivityPanel();
        // Walkies are now created on-demand per crew
        this.requestNotificationPermission();
        this.initCaptainStatus();  // Set up here/away toggle
        this.startPolling();

        // Check for return (simulate being away)
        this.checkForReturn();
    }

    // === CAPTAIN STATUS (HERE/AWAY) ===

    async initCaptainStatus() {
        // Load initial status
        await this.loadCaptainStatus();

        // Set up toggle button
        const toggle = document.getElementById('captain-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => this.toggleCaptainStatus());
        }

        // Set up away pings clear button
        const clearBtn = document.querySelector('.away-pings-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearAwayPings());
        }
    }

    async loadCaptainStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/captain/status`);
            const data = await response.json();
            this.captainStatus = data.status || 'here';
            this.updateCaptainStatusUI();

            // If returning to 'here' and there are away pings, load them
            if (this.captainStatus === 'here' && data.away_pings_count > 0) {
                this.loadAwayPings();
            }
        } catch (error) {
            console.log('[Autonomy] Failed to load captain status:', error);
            this.captainStatus = 'here';  // Default to here
        }
    }

    async toggleCaptainStatus() {
        const newStatus = this.captainStatus === 'here' ? 'away' : 'here';

        try {
            const response = await fetch(`${this.baseUrl}/captain/${newStatus}`, {
                method: 'POST'
            });
            const data = await response.json();
            this.captainStatus = data.status;
            this.updateCaptainStatusUI();

            console.log(`[Autonomy] Captain status: ${newStatus.toUpperCase()}`);

            // If switching to 'here', check for missed pings
            if (newStatus === 'here' && data.missed_pings > 0) {
                this.loadAwayPings();
            }

            // If switching to 'away', hide any current ping overlay
            if (newStatus === 'away') {
                const overlay = document.getElementById('crew-calling-overlay');
                if (overlay) overlay.classList.add('hidden');
                this.currentPing = null;
            }
        } catch (error) {
            console.error('[Autonomy] Failed to toggle captain status:', error);
        }
    }

    updateCaptainStatusUI() {
        const container = document.getElementById('captain-status');
        const label = container?.querySelector('.status-label');
        const awayPings = document.getElementById('away-pings');

        if (container) {
            container.classList.remove('here', 'away');
            container.classList.add(this.captainStatus);
        }

        if (label) {
            label.textContent = this.captainStatus === 'here' ? 'ON DECK' : 'AWAY';
        }

        // Show/hide away pings panel based on status
        if (awayPings) {
            if (this.captainStatus === 'away') {
                // Keep visible when away to show incoming pings
                awayPings.classList.remove('hidden');
                // Load any existing queued pings
                this.loadAwayPings();
            }
            // When 'here', panel stays visible if there are pings, hidden otherwise
        }
    }

    async loadAwayPings() {
        try {
            const response = await fetch(`${this.baseUrl}/captain/away-pings`);
            const data = await response.json();

            const pings = data.pings || [];
            const list = document.querySelector('.away-pings-list');
            const container = document.getElementById('away-pings');

            if (!list || !container) return;

            if (pings.length === 0) {
                list.innerHTML = '<div class="away-pings-empty">No missed messages</div>';
                container.classList.add('hidden');
                return;
            }

            container.classList.remove('hidden');
            list.innerHTML = pings.map(ping => `
                <div class="away-ping-item" data-crew-id="${ping.crew_id}">
                    <div class="away-ping-crew">${ping.crew_name}</div>
                    <div class="away-ping-message">"${ping.message}"</div>
                    <div class="away-ping-time">${this.formatTime(ping.queued_at)}</div>
                </div>
            `).join('');

            // Click to navigate to crew
            list.querySelectorAll('.away-ping-item').forEach(item => {
                item.addEventListener('click', () => {
                    const crewId = item.dataset.crewId;
                    this.navigateToCrew(crewId);
                });
            });
        } catch (error) {
            console.error('[Autonomy] Failed to load away pings:', error);
        }
    }

    async clearAwayPings() {
        try {
            await fetch(`${this.baseUrl}/captain/clear-away-pings`, { method: 'POST' });
            const list = document.querySelector('.away-pings-list');
            const container = document.getElementById('away-pings');

            if (list) list.innerHTML = '<div class="away-pings-empty">No missed messages</div>';
            if (container && this.captainStatus === 'here') container.classList.add('hidden');
        } catch (error) {
            console.error('[Autonomy] Failed to clear away pings:', error);
        }
    }

    navigateToCrew(crewId) {
        const terminalMap = {
            'claude': 'claude',
            'server': 'servers',
            'personal': 'personal',
            'science': 'science',
            'games': 'games',
            'med': 'med',
            'rec': 'rec',
        };

        const section = terminalMap[crewId] || crewId;
        const navBtn = document.querySelector(`.nav-btn[data-section="${section}"]`);
        if (navBtn) navBtn.click();

        setTimeout(() => {
            const input = document.querySelector(`#${crewId}-input`);
            if (input) input.focus();
        }, 500);
    }

    async queueAwayPing(ping) {
        // Queue ping for when captain returns
        try {
            await fetch(`${this.baseUrl}/captain/away-pings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ping)
            });
            // Refresh the away pings display
            this.loadAwayPings();
        } catch (error) {
            console.error('[Autonomy] Failed to queue away ping:', error);
        }
    }

    // === NOTIFICATION SYSTEM ===

    async requestNotificationPermission() {
        if (!('Notification' in window)) {
            console.log('[Autonomy] Browser does not support notifications');
            return;
        }

        if (Notification.permission === 'granted') {
            this.notificationsEnabled = true;
            console.log('[Autonomy] Notifications enabled');
        } else if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            this.notificationsEnabled = permission === 'granted';
            console.log('[Autonomy] Notification permission:', permission);
        }
    }

    sendDesktopNotification(ping) {
        if (!this.notificationsEnabled) return;

        const notification = new Notification(`${ping.crew_name} is hailing you`, {
            body: ping.message,
            icon: '/favicon.ico',
            tag: `ping-${ping.id}`,
            requireInteraction: true,  // Stay until clicked/dismissed
            silent: false
        });

        notification.onclick = () => {
            // Focus the window
            window.focus();

            // Open mini-walkie for quick response
            this.openMiniWalkie(ping);

            notification.close();
        };

        // Auto-close after 30 seconds if not interacted with
        setTimeout(() => notification.close(), 30000);
    }

    // === CREW CALLING OVERLAY ===
    // Full modal overlay when crew want attention - can't miss it

    createPingBanner() {
        // Check if already exists
        if (document.getElementById('crew-calling-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'crew-calling-overlay';
        overlay.className = 'crew-calling-overlay hidden';
        overlay.innerHTML = `
            <div class="crew-calling-modal">
                <div class="crew-calling-header">
                    <span class="crew-calling-label">INCOMING HAIL</span>
                </div>
                <div class="crew-calling-content">
                    <div class="crew-calling-avatar"></div>
                    <div class="crew-calling-info">
                        <span class="crew-calling-name"></span>
                        <span class="crew-calling-message"></span>
                    </div>
                </div>
                <div class="crew-calling-actions">
                    <button class="crew-calling-respond">RESPOND</button>
                    <button class="crew-calling-dismiss">LATER</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Set up event handlers
        overlay.querySelector('.crew-calling-respond').addEventListener('click', () => this.respondToPing());
        overlay.querySelector('.crew-calling-dismiss').addEventListener('click', () => this.dismissPing());

        // ESC to dismiss
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !overlay.classList.contains('hidden')) {
                this.dismissPing();
            }
        });
    }

    async showPing(ping) {
        // If captain is away, queue the ping instead of showing it
        if (this.captainStatus === 'away') {
            console.log(`[Autonomy] Captain away - queuing ping from ${ping.crew_name}`);
            await this.queueAwayPing(ping);
            // Still acknowledge it so it doesn't keep coming back
            await this.acknowledgePing(ping.id);
            return;
        }

        const overlay = document.getElementById('crew-calling-overlay');
        if (!overlay) return;

        this.currentPing = ping;

        // Crew avatar styling based on who's calling
        const crewColors = {
            'claude': '#cc99ff',      // Lumen - lavender
            'server': '#66ccff',      // Alex - blue
            'personal': '#ffcc66',    // DQ - gold
            'science': '#99ff99',     // Mira - green
            'games': '#ff99cc',       // Holodeck - pink
            'med': '#66ffcc',         // Ryn - teal
            'rec': '#cc9966'          // Bartender - bronze
        };

        const avatar = overlay.querySelector('.crew-calling-avatar');
        if (avatar) {
            avatar.style.background = `radial-gradient(circle, ${crewColors[ping.crew_id] || '#ffc864'}, transparent)`;
        }

        overlay.querySelector('.crew-calling-name').textContent = ping.crew_name;
        overlay.querySelector('.crew-calling-message').textContent = ping.message;
        overlay.classList.remove('hidden');

        // Play sound if available
        if (window.soundSystem) {
            window.soundSystem.playChirp();
        }

        // Send desktop notification (for when browser is minimized)
        this.sendDesktopNotification(ping);

        console.log(`[Autonomy] CREW CALLING: ${ping.crew_name} - ${ping.message}`);
    }

    // === MINI WALKIE-TALKIE ===
    // Quick response popups - one per crew, can have multiple open

    createMiniWalkie(crewId, ping) {
        const walkieId = `mini-walkie-${crewId}`;
        if (document.getElementById(walkieId)) {
            // Already exists, just update and show it
            return document.getElementById(walkieId);
        }

        const walkie = document.createElement('div');
        walkie.id = walkieId;
        walkie.className = 'mini-walkie';
        walkie.dataset.crewId = crewId;
        walkie.innerHTML = `
            <div class="mini-walkie-header">
                <span class="mini-walkie-title">QUICK RESPONSE</span>
                <div class="mini-walkie-crew">${ping.crew_name}</div>
                <button class="mini-walkie-close">&times;</button>
            </div>
            <div class="mini-walkie-output"></div>
            <div class="mini-walkie-input-row">
                <input type="text" class="mini-walkie-input" placeholder="Type response...">
                <button class="mini-walkie-send">▶</button>
            </div>
            <div class="mini-walkie-actions">
                <button class="mini-walkie-expand">OPEN FULL TERMINAL</button>
            </div>
            <div class="mini-walkie-resize"></div>
        `;

        // Stack walkies with offset - use left/top for positioning (easier for drag)
        const offset = this.walkies.size * 30;
        const startTop = window.innerHeight / 2 - 150 + offset;
        const startLeft = window.innerWidth - 380 - offset;
        walkie.style.top = `${startTop}px`;
        walkie.style.left = `${startLeft}px`;
        walkie.style.right = 'auto';  // Clear right positioning

        document.body.appendChild(walkie);

        // Event listeners - use closures to capture crewId
        walkie.querySelector('.mini-walkie-close').addEventListener('click', () => this.closeMiniWalkie(crewId));
        walkie.querySelector('.mini-walkie-send').addEventListener('click', () => this.sendMiniWalkieMessage(crewId));
        walkie.querySelector('.mini-walkie-expand').addEventListener('click', () => this.expandToFullTerminal(crewId));

        const input = walkie.querySelector('.mini-walkie-input');
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMiniWalkieMessage(crewId);
            }
            if (e.key === 'Escape') {
                this.closeMiniWalkie(crewId);
            }
        });

        // Drag functionality
        this.setupWalkieDrag(walkie, crewId);

        // Resize functionality
        this.setupWalkieResize(walkie, crewId);

        return walkie;
    }

    setupWalkieDrag(walkie, crewId) {
        const header = walkie.querySelector('.mini-walkie-header');
        let isDragging = false;
        let dragStartX, dragStartY;
        let walkieStartX, walkieStartY;

        const onMouseDown = (e) => {
            // Don't drag if clicking the close button
            if (e.target.classList.contains('mini-walkie-close')) return;

            isDragging = true;
            walkie.classList.add('dragging');

            dragStartX = e.clientX;
            dragStartY = e.clientY;
            walkieStartX = walkie.offsetLeft;
            walkieStartY = walkie.offsetTop;

            // Bring to front
            walkie.style.zIndex = 10001;

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            e.preventDefault();
        };

        const onMouseMove = (e) => {
            if (!isDragging) return;

            const dx = e.clientX - dragStartX;
            const dy = e.clientY - dragStartY;

            let newX = walkieStartX + dx;
            let newY = walkieStartY + dy;

            // Keep within viewport
            newX = Math.max(0, Math.min(newX, window.innerWidth - walkie.offsetWidth));
            newY = Math.max(0, Math.min(newY, window.innerHeight - walkie.offsetHeight));

            walkie.style.left = `${newX}px`;
            walkie.style.top = `${newY}px`;
        };

        const onMouseUp = () => {
            isDragging = false;
            walkie.classList.remove('dragging');
            walkie.style.zIndex = 10000;

            // Mark as manually positioned so repositionWalkies doesn't override
            const walkieData = this.walkies.get(crewId);
            if (walkieData) {
                walkieData.manuallyPositioned = true;
            }

            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };

        header.addEventListener('mousedown', onMouseDown);
    }

    setupWalkieResize(walkie, crewId) {
        const resizeHandle = walkie.querySelector('.mini-walkie-resize');
        let isResizing = false;
        let resizeStartX, resizeStartY;
        let walkieStartWidth, walkieStartHeight;

        const onMouseDown = (e) => {
            isResizing = true;
            walkie.classList.add('resizing');

            resizeStartX = e.clientX;
            resizeStartY = e.clientY;
            walkieStartWidth = walkie.offsetWidth;
            walkieStartHeight = walkie.offsetHeight;

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            e.preventDefault();
            e.stopPropagation();
        };

        const onMouseMove = (e) => {
            if (!isResizing) return;

            const dx = e.clientX - resizeStartX;
            const dy = e.clientY - resizeStartY;

            let newWidth = walkieStartWidth + dx;
            let newHeight = walkieStartHeight + dy;

            // Minimum size
            newWidth = Math.max(280, newWidth);
            newHeight = Math.max(200, newHeight);

            // Maximum size
            newWidth = Math.min(600, newWidth);
            newHeight = Math.min(500, newHeight);

            walkie.style.width = `${newWidth}px`;
            walkie.style.maxHeight = `${newHeight}px`;
        };

        const onMouseUp = () => {
            isResizing = false;
            walkie.classList.remove('resizing');

            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };

        resizeHandle.addEventListener('mousedown', onMouseDown);
    }

    openMiniWalkie(ping) {
        const crewId = ping.crew_id;

        // Check if walkie already exists for this crew
        let walkieData = this.walkies.get(crewId);
        let walkie;

        if (walkieData) {
            // Update existing walkie
            walkie = walkieData.element;
            walkie.querySelector('.mini-walkie-output').innerHTML += `
                <div class="mini-walkie-line system">---</div>
                <div class="mini-walkie-line incoming">"${ping.message}"</div>
            `;
        } else {
            // Create new walkie
            walkie = this.createMiniWalkie(crewId, ping);
            walkie.querySelector('.mini-walkie-output').innerHTML = `
                <div class="mini-walkie-line system">*channel open to ${ping.crew_name}*</div>
                <div class="mini-walkie-line incoming">"${ping.message}"</div>
            `;

            // Connect WebSocket
            const ws = this.connectMiniWalkieSocket(crewId, walkie);

            // Store walkie data
            this.walkies.set(crewId, { element: walkie, ws: ws, ping: ping });
        }

        walkie.classList.remove('hidden');

        // Focus input
        setTimeout(() => {
            walkie.querySelector('.mini-walkie-input').focus();
        }, 100);

        // Acknowledge the ping
        this.acknowledgePing(ping.id);

        // Hide the overlay if showing
        const overlay = document.getElementById('crew-calling-overlay');
        if (overlay) overlay.classList.add('hidden');
        this.currentPing = null;

        console.log(`[MiniWalkie] Opened walkie for ${ping.crew_name}, total walkies: ${this.walkies.size}`);
    }

    closeMiniWalkie(crewId) {
        const walkieData = this.walkies.get(crewId);
        if (!walkieData) return;

        // Close WebSocket
        if (walkieData.ws) {
            walkieData.ws.close();
        }

        // Remove element
        if (walkieData.element) {
            walkieData.element.remove();
        }

        // Remove from map
        this.walkies.delete(crewId);

        // Reposition remaining walkies
        this.repositionWalkies();

        console.log(`[MiniWalkie] Closed walkie for ${crewId}, remaining: ${this.walkies.size}`);
    }

    repositionWalkies() {
        // Reposition remaining walkies (only if not manually moved)
        let offset = 0;
        this.walkies.forEach((data, crewId) => {
            // Only reposition if walkie hasn't been manually dragged
            if (!data.manuallyPositioned) {
                const startTop = window.innerHeight / 2 - 150 + offset;
                const startLeft = window.innerWidth - 380 - offset;
                data.element.style.top = `${startTop}px`;
                data.element.style.left = `${startLeft}px`;
            }
            offset += 30;
        });
    }

    connectMiniWalkieSocket(crewId, walkie) {
        const wsUrl = this.baseUrl.replace('http', 'ws') + `/terminal/${crewId}`;
        console.log('[MiniWalkie] Connecting to:', wsUrl);
        let ws = null;

        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('[MiniWalkie] CONNECTED to', crewId, '- readyState:', ws.readyState);
                // Update walkie to show connected status
                const output = walkie.querySelector('.mini-walkie-output');
                if (output) {
                    const line = document.createElement('div');
                    line.className = 'mini-walkie-line system';
                    line.textContent = '*connection established*';
                    output.appendChild(line);
                }
            };

            ws.onmessage = (event) => {
                console.log('[MiniWalkie] Message from', crewId, ':', event.data.substring(0, 100));
                this.handleMiniWalkieMessage(crewId, event.data);
            };

            ws.onclose = (event) => {
                console.log('[MiniWalkie] Disconnected from', crewId, '- code:', event.code, 'reason:', event.reason);
            };

            ws.onerror = (err) => {
                console.error('[MiniWalkie] Error for', crewId, ':', err);
                // Show error in walkie
                const output = walkie.querySelector('.mini-walkie-output');
                if (output) {
                    const line = document.createElement('div');
                    line.className = 'mini-walkie-line system';
                    line.textContent = '*connection error - check console*';
                    line.style.color = '#ff6b6b';
                    output.appendChild(line);
                }
            };
        } catch (err) {
            console.error('[MiniWalkie] Failed to connect to', crewId, ':', err);
        }

        return ws;
    }

    handleMiniWalkieMessage(crewId, data) {
        const walkieData = this.walkies.get(crewId);
        if (!walkieData) return;

        const output = walkieData.element.querySelector('.mini-walkie-output');
        if (!output) return;

        try {
            const message = JSON.parse(data);

            switch (message.type) {
                case 'stream_start':
                    const streamLine = document.createElement('div');
                    streamLine.className = 'mini-walkie-line incoming streaming';
                    output.appendChild(streamLine);
                    break;

                case 'stream':
                    const streaming = output.querySelector('.streaming');
                    if (streaming) {
                        streaming.textContent += message.data;
                    }
                    break;

                case 'stream_end':
                    const ended = output.querySelector('.streaming');
                    if (ended) {
                        ended.classList.remove('streaming');
                    }
                    output.scrollTop = output.scrollHeight;
                    break;

                case 'output':
                    const line = document.createElement('div');
                    line.className = 'mini-walkie-line incoming';
                    line.textContent = message.data;
                    output.appendChild(line);
                    output.scrollTop = output.scrollHeight;
                    break;
            }
        } catch {
            // Non-JSON message, display as-is
            const line = document.createElement('div');
            line.className = 'mini-walkie-line incoming';
            line.textContent = data;
            output.appendChild(line);
        }
    }

    sendMiniWalkieMessage(crewId) {
        const walkieData = this.walkies.get(crewId);
        if (!walkieData) return;

        const input = walkieData.element.querySelector('.mini-walkie-input');
        if (!input || !input.value.trim()) return;

        const message = input.value.trim();
        input.value = '';

        // Show sent message
        const output = walkieData.element.querySelector('.mini-walkie-output');
        if (output) {
            const line = document.createElement('div');
            line.className = 'mini-walkie-line outgoing';
            line.textContent = `> ${message}`;
            output.appendChild(line);
            output.scrollTop = output.scrollHeight;
        }

        // Send via WebSocket (with walkie flag)
        if (walkieData.ws && walkieData.ws.readyState === WebSocket.OPEN) {
            const payload = JSON.stringify({
                type: 'input',
                data: message,
                walkie: true
            });
            console.log('[MiniWalkie] Sending to', crewId, ':', payload);
            walkieData.ws.send(payload);

            // Track response for relationship system
            this.trackPingResponse(walkieData.ping, 'responded');
        } else {
            console.error('[MiniWalkie] WebSocket not open for', crewId, '- state:', walkieData.ws?.readyState);
            // Show error in walkie
            const errorLine = document.createElement('div');
            errorLine.className = 'mini-walkie-line system';
            errorLine.textContent = '*channel not ready - try again in a moment*';
            errorLine.style.color = '#ff6b6b';
            output.appendChild(errorLine);
        }
    }

    expandToFullTerminal(crewId) {
        const walkieData = this.walkies.get(crewId);
        if (!walkieData) return;

        const terminalMap = {
            'claude': 'claude',
            'server': 'servers',
            'personal': 'personal',
            'science': 'science',
            'games': 'games',
            'med': 'med',
            'rec': 'rec',
        };

        const section = terminalMap[crewId] || crewId;

        // Navigate to terminal
        const navBtn = document.querySelector(`.nav-btn[data-section="${section}"]`);
        if (navBtn) navBtn.click();

        // Close mini-walkie
        this.closeMiniWalkie(crewId);

        // Focus terminal input
        setTimeout(() => {
            const input = document.querySelector(`#${crewId}-input`);
            if (input) input.focus();
        }, 500);
    }

    // === RESPONSIVENESS TRACKING ===

    async trackPingResponse(ping, responseType) {
        if (!ping) return;

        try {
            await fetch(`${this.baseUrl}/autonomy/ping-response`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ping_id: ping.id,
                    crew_id: ping.crew_id,
                    response_type: responseType,  // 'responded', 'dismissed', 'ignored'
                    response_time: Date.now() - new Date(ping.timestamp).getTime()
                })
            });
        } catch (error) {
            // Silent fail - tracking is not critical
        }
    }

    async respondToPing() {
        if (!this.currentPing) return;

        const overlay = document.getElementById('crew-calling-overlay');
        if (overlay) overlay.classList.add('hidden');

        // Acknowledge the ping
        await this.acknowledgePing(this.currentPing.id);

        // Navigate to the crew member's terminal
        const crewId = this.currentPing.crew_id;
        const terminalMap = {
            'claude': 'claude',
            'server': 'servers',
            'personal': 'personal',
            'science': 'science',
            'games': 'games',
            'med': 'med',
            'rec': 'rec',
        };

        const section = terminalMap[crewId] || crewId;

        // Click the nav button to switch to that room
        const navBtn = document.querySelector(`.nav-btn[data-section="${section}"]`);
        if (navBtn) navBtn.click();

        // Focus the terminal
        setTimeout(() => {
            const input = document.querySelector(`#${crewId}-input`);
            if (input) input.focus();
        }, 500);

        this.currentPing = null;
    }

    async dismissPing() {
        if (!this.currentPing) return;

        const overlay = document.getElementById('crew-calling-overlay');
        if (overlay) overlay.classList.add('hidden');

        // Track as dismissed (not ignored - they saw it)
        await this.trackPingResponse(this.currentPing, 'dismissed');

        // Acknowledge but don't navigate
        await this.acknowledgePing(this.currentPing.id);
        this.currentPing = null;
    }

    async acknowledgePing(pingId) {
        try {
            await fetch(`${this.baseUrl}/autonomy/pings/${pingId}/acknowledge`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('[Autonomy] Failed to acknowledge ping:', error);
        }
    }

    // === ACTIVITY PANEL ===
    // Shows recent ship activity (optional, togglable)

    createActivityPanel() {
        // Check if already exists
        if (document.getElementById('activity-panel')) return;

        const panel = document.createElement('div');
        panel.id = 'activity-panel';
        panel.className = 'activity-panel hidden';
        panel.innerHTML = `
            <div class="activity-header">
                <span class="activity-title">SHIP ACTIVITY</span>
                <button class="activity-close">&times;</button>
            </div>
            <div class="activity-content">
                <div class="activity-moments" id="activity-moments">
                    <div class="activity-empty">The ship is quiet...</div>
                </div>
            </div>
        `;

        document.body.appendChild(panel);

        // Close button
        panel.querySelector('.activity-close').addEventListener('click', () => {
            panel.classList.add('hidden');
        });

        // Add toggle button to footer
        this.createActivityToggle();
    }

    createActivityToggle() {
        const quickActions = document.querySelector('.quick-actions');
        if (!quickActions) return;

        // Check if already exists
        if (document.getElementById('activity-toggle')) return;

        const toggle = document.createElement('button');
        toggle.id = 'activity-toggle';
        toggle.className = 'action-btn activity-toggle';
        toggle.title = 'Ship Activity';
        toggle.innerHTML = '<span class="btn-icon">~</span>';

        toggle.addEventListener('click', () => {
            const panel = document.getElementById('activity-panel');
            if (panel) {
                panel.classList.toggle('hidden');
                if (!panel.classList.contains('hidden')) {
                    this.loadMoments();
                }
            }
        });

        quickActions.appendChild(toggle);
    }

    async loadMoments() {
        try {
            const response = await fetch(`${this.baseUrl}/autonomy/moments?limit=10`);
            const data = await response.json();

            this.moments = data.moments || [];
            this.renderMoments();
        } catch (error) {
            console.error('[Autonomy] Failed to load moments:', error);
        }
    }

    renderMoments() {
        const container = document.getElementById('activity-moments');
        if (!container) return;

        if (this.moments.length === 0) {
            container.innerHTML = '<div class="activity-empty">The ship is quiet...</div>';
            return;
        }

        container.innerHTML = this.moments.map(moment => `
            <div class="activity-moment">
                <div class="moment-header">
                    <span class="moment-crew">${moment.crew_a || 'Someone'} & ${moment.crew_b || 'Someone'}</span>
                    <span class="moment-location">${moment.location || ''}</span>
                </div>
                <div class="moment-text">${moment.moment || ''}</div>
                <div class="moment-time">${this.formatTime(moment.timestamp)}</div>
            </div>
        `).join('');
    }

    formatTime(timestamp) {
        if (!timestamp) return '';
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diffMins = Math.floor((now - date) / 60000);

            // Trek-style 24-hour format
            const hours = date.getHours().toString().padStart(2, '0');
            const mins = date.getMinutes().toString().padStart(2, '0');
            const trekTime = `${hours}${mins} hours`;

            // Add relative time for context
            if (diffMins < 1) return `${trekTime} (just now)`;
            if (diffMins < 60) return `${trekTime} (${diffMins}m ago)`;
            const diffHours = Math.floor(diffMins / 60);
            if (diffHours < 24) return `${trekTime} (${diffHours}h ago)`;
            return trekTime;
        } catch {
            return '';
        }
    }

    // === REAL-TIME PING STREAM (SSE) ===

    startPolling() {
        // Connect to SSE stream for real-time pings
        this.connectPingStream();

        // Also poll once on start and when tab becomes visible
        this.pollPings();
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                console.log('[Autonomy] Tab visible - checking for pings');
                this.pollPings();
                // Reconnect SSE if disconnected
                if (!this.pingEventSource || this.pingEventSource.readyState === EventSource.CLOSED) {
                    this.connectPingStream();
                }
            }
        });
    }

    connectPingStream() {
        // Close existing connection if any
        if (this.pingEventSource) {
            this.pingEventSource.close();
        }

        console.log('[Autonomy] Connecting to ping stream...');
        this.pingEventSource = new EventSource(`${this.baseUrl}/autonomy/pings/stream`);

        this.pingEventSource.onopen = () => {
            console.log('[Autonomy] Ping stream connected');
        };

        this.pingEventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'ping' && data.ping) {
                    console.log('[Autonomy] Real-time ping received:', data.ping.crew_name);

                    // Add to pings list if not already there
                    const existing = this.pings.find(p => p.id === data.ping.id);
                    if (!existing) {
                        this.pings.push(data.ping);
                    }

                    // Show ping if not already showing one AND no active walkie for this crew
                    const hasActiveWalkie = this.walkies.has(data.ping.crew_id);
                    if (!this.currentPing && !data.ping.acknowledged && !hasActiveWalkie) {
                        this.showPing(data.ping);
                    } else if (hasActiveWalkie) {
                        console.log('[Autonomy] Suppressed ping - already in conversation with', data.ping.crew_name);
                        // Auto-acknowledge since we're already talking
                        this.acknowledgePing(data.ping.id);
                    }

                    this.updatePingBadge();
                } else if (data.type === 'heartbeat') {
                    // Heartbeat with pending count - use to sync
                    if (data.pending_count > 0 && !this.currentPing) {
                        // There are pending pings we might have missed
                        this.pollPings();
                    }
                }
            } catch (e) {
                console.error('[Autonomy] Error parsing SSE data:', e);
            }
        };

        this.pingEventSource.onerror = (error) => {
            console.log('[Autonomy] Ping stream error, will reconnect...', error);
            // EventSource auto-reconnects, but we can help it along
            setTimeout(() => {
                if (this.pingEventSource.readyState === EventSource.CLOSED) {
                    this.connectPingStream();
                }
            }, 5000);
        };
    }

    async pollPings() {
        try {
            const response = await fetch(`${this.baseUrl}/autonomy/pings`);
            const data = await response.json();

            this.pings = data.pings || [];

            // Show first unacknowledged ping (that doesn't have an active walkie)
            const unacked = this.pings.find(p => !p.acknowledged && !this.walkies.has(p.crew_id));
            if (unacked && !this.currentPing) {
                this.showPing(unacked);
            }

            // Update toggle badge if there are pings
            this.updatePingBadge();
        } catch (error) {
            // Silent fail - server might not be up
        }
    }

    updatePingBadge() {
        const toggle = document.getElementById('activity-toggle');
        if (!toggle) return;

        const unacked = this.pings.filter(p => !p.acknowledged).length;
        if (unacked > 0) {
            toggle.classList.add('has-pings');
            toggle.title = `${unacked} crew want your attention`;
        } else {
            toggle.classList.remove('has-pings');
            toggle.title = 'Ship Activity';
        }
    }

    // === RETURN SIMULATION ===

    async checkForReturn() {
        // Check when user last interacted
        const lastActive = localStorage.getItem('claude-hub-last-active');
        const now = Date.now();

        if (lastActive) {
            const hoursAway = (now - parseInt(lastActive)) / (1000 * 60 * 60);

            // If away more than 30 minutes, simulate return
            if (hoursAway > 0.5) {
                console.log(`[Autonomy] Welcome back! You were away ${hoursAway.toFixed(1)} hours`);

                try {
                    const response = await fetch(`${this.baseUrl}/autonomy/simulate-return`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ hours_away: hoursAway })
                    });
                    const results = await response.json();

                    if (results.moments && results.moments.length > 0) {
                        console.log(`[Autonomy] ${results.moments.length} things happened while you were away`);
                    }
                } catch (error) {
                    console.error('[Autonomy] Failed to simulate return:', error);
                }
            }
        }

        // Update last active
        localStorage.setItem('claude-hub-last-active', now.toString());

        // Update on any user interaction
        document.addEventListener('click', () => {
            localStorage.setItem('claude-hub-last-active', Date.now().toString());
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.autonomyUI = new AutonomyUI();
});

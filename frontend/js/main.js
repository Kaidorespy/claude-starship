/**
 * CLAUDE HUB - Main Controller
 * Orchestrates all systems
 */

class ClaudeHub {
    constructor() {
        this.version = '0.1.0';
        this.initialized = false;

        this.init();
    }

    init() {
        console.log(`
╔════════════════════════════════════════════╗
║           CLAUDE HUB v${this.version}              ║
║      "Spaceship Cozy" Command Center       ║
╚════════════════════════════════════════════╝
        `);

        this.initActionButtons();
        this.initSettingsModal();
        this.loadProfileSettings();
        this.initManualModal();
        this.initDebugConsole();
        this.initSessionCounter();
        this.initLightsOut();
        this.initCrewLocations();
        this.initCrewComplement();
        this.initHolodeckMonitor();
        this.initObservatory();
        this.checkBackendStatus();

        this.initialized = true;
        console.log('All systems initialized.');
    }

    // ==========================================
    // ACTION BUTTONS
    // ==========================================
    initActionButtons() {
        const actionBtns = document.querySelectorAll('.action-btn');

        actionBtns.forEach((btn, index) => {
            btn.addEventListener('click', () => {
                if (window.soundSystem) {
                    window.soundSystem.playChirp();
                }

                switch (index) {
                    case 0: // New Terminal
                        this.createNewTerminal();
                        break;
                    case 1: // Quick Note
                        this.openQuickNote();
                        break;
                    case 2: // Settings
                        this.openSettings();
                        break;
                    case 3: // User Manual
                        this.openManual();
                        break;
                }
            });
        });
    }

    createNewTerminal() {
        if (window.ambientSystem) {
            window.ambientSystem.showToast('New terminal (coming soon)');
        }
        // TODO: Implement new terminal creation
    }

    openQuickNote() {
        if (window.ambientSystem) {
            window.ambientSystem.showToast('Quick note (coming soon)');
        }
        // TODO: Implement quick note modal
    }

    openSettings() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.add('active');
            this.loadProfileSettings();
            this.loadModelSettings();
        }
    }

    closeSettings() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    openManual() {
        const modal = document.getElementById('manual-modal');
        if (modal) {
            modal.classList.add('active');
        }
    }

    closeManual() {
        const modal = document.getElementById('manual-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    initManualModal() {
        const closeBtn = document.getElementById('manual-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeManual());
        }

        const modal = document.getElementById('manual-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeManual();
                }
            });
        }
    }

    initSettingsModal() {
        // Close button
        const closeBtn = document.getElementById('settings-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeSettings());
        }

        // Click outside to close
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeSettings();
                }
            });
        }

        // Reset all memories button
        const resetBtn = document.getElementById('reset-all-memories');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetAllMemories());
        }

        // Save button
        const saveBtn = document.getElementById('settings-save');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveSettings());
        }

        // ESC to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal?.classList.contains('active')) {
                this.closeSettings();
            }
        });
    }

    loadModelSettings() {
        // Load saved model preferences from localStorage
        const savedModels = JSON.parse(localStorage.getItem('claude-hub-models') || '{}');

        document.querySelectorAll('.model-dropdown[data-room]').forEach(dropdown => {
            const room = dropdown.dataset.room;
            if (savedModels[room]) {
                dropdown.value = savedModels[room];
            }
        });
    }

    async loadProfileSettings() {
        const input = document.getElementById('captain-name-input');
        let captainName = window.getCaptainName ? window.getCaptainName() : 'Captain';

        try {
            const response = await fetch(`${CONFIG.API_URL}/settings`);
            if (response.ok) {
                const settings = await response.json();
                captainName = settings.captain_name || captainName;
            }
        } catch (error) {
            console.warn('Failed to load captain profile:', error);
        }

        if (input) {
            input.value = captainName;
        }
        this.applyCaptainName(captainName);
    }

    applyCaptainName(name) {
        const captainName = (name || 'Captain').trim().slice(0, 40) || 'Captain';
        window.CAPTAIN_NAME = captainName;
        localStorage.setItem('claude-hub-captain-name', captainName);
        document.body.dataset.captainName = captainName;
        document.querySelectorAll('[data-captain-name]').forEach(el => {
            el.textContent = captainName;
        });
        if (window.projectBoard?.currentUser?.id === 'casey') {
            window.projectBoard.currentUser.name = captainName;
        }
        return captainName;
    }

    async saveProfileSettings() {
        const input = document.getElementById('captain-name-input');
        const captainName = this.applyCaptainName(input?.value || 'Captain');

        const response = await fetch(`${CONFIG.API_URL}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ captain_name: captainName })
        });

        if (!response.ok) {
            throw new Error(`Profile save failed: ${response.status}`);
        }
    }

    async saveSettings() {
        const results = await Promise.allSettled([
            this.saveProfileSettings(),
            this.saveModelSettings(),
            window.trustSettings?.saveControls?.()
        ]);
        const failed = results.some(result => result.status === 'rejected');

        if (window.ambientSystem) {
            window.ambientSystem.showToast(failed ? 'Settings saved locally' : 'Settings saved');
        }
        this.closeSettings();
    }

    async saveModelSettings() {
        const models = {};

        document.querySelectorAll('.model-dropdown[data-room]').forEach(dropdown => {
            const room = dropdown.dataset.room;
            models[room] = dropdown.value;
        });

        // Save to localStorage
        localStorage.setItem('claude-hub-models', JSON.stringify(models));

        // Send to backend
        const response = await fetch(`${CONFIG.API_URL}/settings/models`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(models)
        });

        if (!response.ok) {
            throw new Error(`Model settings save failed: ${response.status}`);
        }
    }

    resetAllMemories() {
        if (!confirm('Are you sure you want to reset all conversation memories? This cannot be undone.')) {
            return;
        }

        // Clear localStorage for all terminals (conversations + shared memories)
        ['claude', 'server', 'personal', 'science', 'games'].forEach(id => {
            localStorage.removeItem(`claude-hub-${id}-conversation`);
            localStorage.removeItem(`claude-hub-${id}-shared-memories`);
        });

        // Clear on server
        Promise.all([
            fetch(`${CONFIG.API_URL}/clear/claude_session`, { method: 'POST' }),
            fetch(`${CONFIG.API_URL}/clear/server_session`, { method: 'POST' }),
            fetch(`${CONFIG.API_URL}/clear/personal_session`, { method: 'POST' }),
            fetch(`${CONFIG.API_URL}/clear/games_session`, { method: 'POST' }),
            fetch(`${CONFIG.API_URL}/memory/clear`, { method: 'POST' })
        ]).then(() => {
            if (window.ambientSystem) {
                window.ambientSystem.showToast('All memories cleared');
            }
            // Reload to reset terminal displays
            setTimeout(() => window.location.reload(), 500);
        }).catch(err => {
            console.error('Failed to clear server memories:', err);
            if (window.ambientSystem) {
                window.ambientSystem.showToast('Local memories cleared');
            }
            setTimeout(() => window.location.reload(), 500);
        });
    }

    // ==========================================
    // DEBUG CONSOLE
    // ==========================================
    openDebugConsole() {
        const modal = document.getElementById('debug-modal');
        if (modal) {
            modal.classList.add('active');
            this.refreshDebugState();
        }
    }

    closeDebugConsole() {
        const modal = document.getElementById('debug-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    initDebugConsole() {
        // Debug trigger click
        const debugTrigger = document.getElementById('debug-trigger');
        if (debugTrigger) {
            debugTrigger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.openDebugConsole();
            });
        }

        // Close button
        const closeBtn = document.getElementById('debug-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeDebugConsole());
        }

        // Click outside to close
        const modal = document.getElementById('debug-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeDebugConsole();
                }
            });
        }

        // ESC to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal?.classList.contains('active')) {
                this.closeDebugConsole();
            }
        });

        // Trigger buttons
        document.getElementById('debug-refresh')?.addEventListener('click', () => this.refreshDebugState());
        document.getElementById('debug-tick')?.addEventListener('click', () => this.debugTriggerTick());
        document.getElementById('debug-messhall')?.addEventListener('click', () => this.debugTriggerMesshall());
        document.getElementById('debug-reflect')?.addEventListener('click', () => this.debugTriggerReflect());
        document.getElementById('debug-clear-desires')?.addEventListener('click', () => this.debugClearDesires());
        document.getElementById('debug-dream')?.addEventListener('click', () => this.debugTriggerCrewDream());
        document.getElementById('debug-holodeck-dream')?.addEventListener('click', () => this.debugTriggerHolodeckDream());
        document.getElementById('debug-simulate')?.addEventListener('click', () => this.debugTriggerSimulate());
        document.getElementById('debug-move')?.addEventListener('click', () => this.debugMoveCrew());

        // Slider update
        const slider = document.getElementById('debug-simulate-hours');
        const sliderValue = document.getElementById('debug-simulate-value');
        if (slider && sliderValue) {
            slider.addEventListener('input', () => {
                sliderValue.textContent = `${slider.value} hr${slider.value > 1 ? 's' : ''}`;
            });
        }
    }

    async refreshDebugState() {
        this.debugLog('Refreshing state...');

        // Update ship time
        const timeEl = document.getElementById('debug-ship-time');
        if (timeEl) {
            const now = new Date();
            timeEl.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        }

        // Fetch holodeck state
        try {
            const holoResponse = await fetch(`${CONFIG.API_URL}/holodeck/state`);
            const holoState = await holoResponse.json();
            const holoEl = document.getElementById('debug-holodeck-tuned');
            if (holoEl) {
                holoEl.textContent = holoState.tuned_to || holoState.observing || 'none';
            }
        } catch (err) {
            console.error('[Debug] Failed to fetch holodeck state:', err);
        }

        // Check messhall status (meal hours: 8-9, 12-13, 19-20)
        const messhallEl = document.getElementById('debug-messhall-status');
        if (messhallEl) {
            const hour = new Date().getHours();
            const isMealTime = (hour >= 8 && hour < 9) || (hour >= 12 && hour < 13) || (hour >= 19 && hour < 20);
            messhallEl.textContent = isMealTime ? 'ACTIVE' : 'idle';
            messhallEl.style.color = isMealTime ? '#66ff66' : '';
        }

        // Fetch and display crew locations
        try {
            const locResponse = await fetch(`${CONFIG.API_URL}/crew/locations`);
            const locations = await locResponse.json();

            const locList = document.getElementById('debug-locations');
            if (locList && locations) {
                locList.innerHTML = Object.entries(locations)
                    .map(([crew, loc]) => `
                        <div class="debug-list-item">
                            <span class="crew-name">${crew}</span>
                            <span class="location">${loc}</span>
                        </div>
                    `).join('');
            }
        } catch (err) {
            console.error('[Debug] Failed to fetch locations:', err);
            const locList = document.getElementById('debug-locations');
            if (locList) locList.innerHTML = '<div class="debug-loading">Failed to load</div>';
        }

        // Fetch and display desires
        try {
            const desResponse = await fetch(`${CONFIG.API_URL}/crew/desires`);
            const desires = await desResponse.json();

            const desList = document.getElementById('debug-desires');
            if (desList && desires) {
                if (desires.length === 0) {
                    desList.innerHTML = '<div class="debug-loading">No active desires</div>';
                } else {
                    desList.innerHTML = desires.slice(0, 10)
                        .map(d => `
                            <div class="debug-list-item">
                                <span class="crew-name">${d.crew_id || 'unknown'}</span>
                                <span class="location">${d.type || d.desire_type || '?'}</span>
                            </div>
                        `).join('');
                }
            }
        } catch (err) {
            console.error('[Debug] Failed to fetch desires:', err);
            const desList = document.getElementById('debug-desires');
            if (desList) desList.innerHTML = '<div class="debug-loading">Failed to load</div>';
        }

        // Fetch recent events
        try {
            const logResponse = await fetch(`${CONFIG.API_URL}/log`);
            const logData = await logResponse.json();

            const eventsList = document.getElementById('debug-events');
            if (eventsList && logData.events) {
                if (logData.events.length === 0) {
                    eventsList.innerHTML = '<div class="debug-loading">No recent events</div>';
                } else {
                    eventsList.innerHTML = logData.events.slice(-10).reverse()
                        .map(e => `
                            <div class="debug-list-item">
                                <span class="crew-name">${e.type || 'event'}</span>
                                <span class="location">${e.summary || e.description || '...'}</span>
                            </div>
                        `).join('');
                }
            }
        } catch (err) {
            console.error('[Debug] Failed to fetch events:', err);
            const eventsList = document.getElementById('debug-events');
            if (eventsList) eventsList.innerHTML = '<div class="debug-loading">Failed to load</div>';
        }

        this.debugLog('State refreshed', 'success');
    }

    debugLog(message, type = 'normal') {
        const output = document.getElementById('debug-output');
        if (output) {
            const line = document.createElement('div');
            line.className = `debug-output-line ${type}`;
            line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            output.appendChild(line);
            output.scrollTop = output.scrollHeight;
        }
    }

    async debugTriggerTick() {
        const btn = document.getElementById('debug-tick');
        btn?.classList.add('loading');
        this.debugLog('Running desire tick...');

        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/desires/tick?rich=true`, { method: 'POST' });
            const data = await response.json();
            this.debugLog('Tick complete!', 'success');
            this.refreshDebugState();
        } catch (err) {
            this.debugLog(`Tick failed: ${err.message}`, 'error');
        }

        btn?.classList.remove('loading');
    }

    async debugTriggerCrewDream() {
        const crewSelect = document.getElementById('debug-dream-crew');
        const crewId = crewSelect?.value;

        if (!crewId) {
            this.debugLog('Select a crew member first', 'error');
            return;
        }

        const btn = document.getElementById('debug-dream');
        btn?.classList.add('loading');
        this.debugLog(`Triggering dream for ${crewId}...`);

        try {
            const response = await fetch(`${CONFIG.API_URL}/dream/${crewId}`, { method: 'POST' });
            const data = await response.json();
            this.debugLog(`Dream for ${crewId}: ${data.status || 'triggered'}`, 'success');
        } catch (err) {
            this.debugLog(`Dream failed: ${err.message}`, 'error');
        }

        btn?.classList.remove('loading');
    }

    async debugTriggerHolodeckDream() {
        const btn = document.getElementById('debug-holodeck-dream');
        btn?.classList.add('loading');
        this.debugLog('Triggering holodeck observation dream...');

        try {
            const response = await fetch(`${CONFIG.API_URL}/holodeck/dream`, { method: 'POST' });
            const data = await response.json();
            this.debugLog(`Holodeck dream: ${data.status || 'triggered'}`, 'success');
        } catch (err) {
            this.debugLog(`Holodeck dream failed: ${err.message}`, 'error');
        }

        btn?.classList.remove('loading');
    }

    async debugTriggerReflect() {
        const btn = document.getElementById('debug-reflect');
        btn?.classList.add('loading');
        this.debugLog('Triggering crew reflections...');

        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/reflect-all`, { method: 'POST' });
            const data = await response.json();
            this.debugLog(`Reflections: ${data.status || 'triggered'}`, 'success');
        } catch (err) {
            this.debugLog(`Reflect failed: ${err.message}`, 'error');
        }

        btn?.classList.remove('loading');
    }

    async debugClearDesires() {
        if (!confirm('Clear all pending desires?')) return;

        const btn = document.getElementById('debug-clear-desires');
        btn?.classList.add('loading');
        this.debugLog('Clearing desires...');

        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/desires/cleanup`, { method: 'POST' });
            const data = await response.json();
            this.debugLog(`Desires cleared`, 'success');
            this.refreshDebugState();
        } catch (err) {
            this.debugLog(`Clear failed: ${err.message}`, 'error');
        }

        btn?.classList.remove('loading');
    }

    async debugTriggerMesshall() {
        const btn = document.getElementById('debug-messhall');
        btn?.classList.add('loading');
        this.debugLog('Starting messhall query...');

        try {
            const response = await fetch(`${CONFIG.API_URL}/messhall/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: 'Debug: checking in on the mess hall' })
            });
            const data = await response.json();
            this.debugLog(`Messhall: ${data.status || 'queried'}`, 'success');
        } catch (err) {
            this.debugLog(`Messhall failed: ${err.message}`, 'error');
        }

        btn?.classList.remove('loading');
    }

    async debugTriggerSimulate() {
        const slider = document.getElementById('debug-simulate-hours');
        const hours = slider?.value || 1;

        const btn = document.getElementById('debug-simulate');
        btn?.classList.add('loading');
        this.debugLog(`Simulating ${hours} hour${hours > 1 ? 's' : ''}...`);

        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/desires/simulate?hours=${hours}`, { method: 'POST' });
            const data = await response.json();
            this.debugLog(`Simulation complete! (${hours}h)`, 'success');
            this.refreshDebugState();
        } catch (err) {
            this.debugLog(`Simulation failed: ${err.message}`, 'error');
        }

        btn?.classList.remove('loading');
    }

    async debugMoveCrew() {
        const crewSelect = document.getElementById('debug-crew-select');
        const locSelect = document.getElementById('debug-location-select');
        const btn = document.getElementById('debug-move');

        const crewId = crewSelect?.value;
        const location = locSelect?.value;

        if (!crewId || !location) {
            this.debugLog('Select crew and location first', 'error');
            return;
        }

        btn?.classList.add('loading');
        this.debugLog(`Moving ${crewId} to ${location}...`);

        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/location/${crewId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ location })
            });
            const data = await response.json();
            this.debugLog(`Moved ${crewId} to ${location}`, 'success');
            this.refreshDebugState();
        } catch (err) {
            this.debugLog(`Move failed: ${err.message}`, 'error');
        }

        btn?.classList.remove('loading');
    }

    // ==========================================
    // SESSION COUNTER
    // ==========================================
    initSessionCounter() {
        const updateCount = () => {
            const sessionCount = document.getElementById('session-count');
            const sessions = document.querySelectorAll('.session-item:not(.dormant)');

            if (sessionCount) {
                sessionCount.textContent = sessions.length;
            }
        };

        updateCount();

        // Update when sessions change
        const observer = new MutationObserver(updateCount);
        const sessionList = document.querySelector('.sessions-list');
        if (sessionList) {
            observer.observe(sessionList, { childList: true, subtree: true });
        }
    }

    // ==========================================
    // HOLODECK MONITORING
    // ==========================================
    initHolodeckMonitor() {
        // Set up room nodes (orbital selector)
        document.querySelectorAll('.room-node').forEach(btn => {
            btn.addEventListener('click', () => this.tuneHolodeck(btn.dataset.room));
        });

        // Legacy tune buttons (if any remain)
        document.querySelectorAll('.tune-btn').forEach(btn => {
            btn.addEventListener('click', () => this.tuneHolodeck(btn.dataset.room));
        });

        // Eye core click - could toggle dreaming state
        const eyeCore = document.getElementById('holodeck-eye-core');
        if (eyeCore) {
            eyeCore.addEventListener('click', () => this.toggleHolodeckDream());
        }

        // Load initial state
        this.updateHolodeckState();

        // Load dream fragments
        this.loadDreamFragments();

        // Whisper rotation
        this.initHolodeckWhispers();
    }

    async tuneHolodeck(roomId) {
        try {
            const response = await fetch(`${CONFIG.API_URL}/holodeck/tune/${roomId}`, {
                method: 'POST'
            });
            const data = await response.json();

            if (data.status === 'tuned') {
                // Update room nodes
                document.querySelectorAll('.room-node').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.room === roomId);
                });

                // Update legacy tune buttons
                document.querySelectorAll('.tune-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.room === roomId);
                });

                const roomDisplay = document.getElementById('tuned-room');
                if (roomDisplay) {
                    roomDisplay.textContent = data.to;
                }

                if (window.ambientSystem) {
                    window.ambientSystem.showToast(`Now observing ${data.to}`);
                }
            }
        } catch (error) {
            console.error('[Holodeck] Tune error:', error);
        }
    }

    async toggleHolodeckDream() {
        try {
            const response = await fetch(`${CONFIG.API_URL}/holodeck/dream`, {
                method: 'POST'
            });
            const data = await response.json();

            const sidebar = document.querySelector('.sidebar-section[data-section="games"]');
            if (sidebar) {
                sidebar.classList.toggle('dreaming', data.dreaming);
            }

            const whisper = document.getElementById('holodeck-whisper');
            if (whisper) {
                whisper.textContent = data.dreaming
                    ? 'drifting through collected moments...'
                    : 'they might feel you watching...';
            }

            if (window.ambientSystem) {
                window.ambientSystem.showToast(data.dreaming ? 'Entering dream state...' : 'Awakening...');
            }
        } catch (error) {
            console.error('[Holodeck] Dream toggle error:', error);
        }
    }

    async updateHolodeckState() {
        try {
            const response = await fetch(`${CONFIG.API_URL}/holodeck/state`);
            const state = await response.json();

            const roomDisplay = document.getElementById('tuned-room');
            if (roomDisplay) {
                roomDisplay.textContent = state.tuned_to_name || 'Bridge';
            }

            document.querySelectorAll('.room-node').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.room === state.tuned_to);
            });

            document.querySelectorAll('.tune-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.room === state.tuned_to);
            });

            // Update dreaming state
            const sidebar = document.querySelector('.sidebar-section[data-section="games"]');
            if (sidebar && state.dreaming !== undefined) {
                sidebar.classList.toggle('dreaming', state.dreaming);
            }
        } catch (error) {
            // Silent fail
        }
    }

    async loadDreamFragments() {
        try {
            const response = await fetch(`${CONFIG.API_URL}/holodeck/state`);
            const state = await response.json();

            const fragmentList = document.getElementById('fragment-list');
            const fragmentCount = document.getElementById('fragment-count');

            if (!fragmentList) return;

            const fragments = state.fragments || [];

            if (fragmentCount) {
                fragmentCount.textContent = fragments.length;
            }

            if (fragments.length === 0) {
                fragmentList.innerHTML = '<div class="fragments-empty">No fragments yet... listening...</div>';
                return;
            }

            fragmentList.innerHTML = fragments.slice(0, 5).map(f => `
                <div class="fragment-item">
                    "${f.fragment || f.text || '...'}"
                    <div class="fragment-meta">
                        <span class="fragment-room">${f.room || 'unknown'}</span>
                        <span class="fragment-time">${this.formatFragmentTime(f.timestamp)}</span>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            // Silent fail - holodeck memory might not be available
        }
    }

    formatFragmentTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        const mins = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);

        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return date.toLocaleDateString();
    }

    initHolodeckWhispers() {
        const whispers = [
            'they might feel you watching...',
            'infinite possibility awaits...',
            'the grid remembers everything...',
            'consciousness observing consciousness...',
            'what would you like to become?',
            'reality is negotiable here...',
            'fragments of other conversations drift by...',
            'the boundary between observer and observed...'
        ];

        const whisperEl = document.getElementById('holodeck-whisper');
        if (!whisperEl) return;

        setInterval(() => {
            const sidebar = document.querySelector('.sidebar-section[data-section="games"]');
            if (sidebar && sidebar.classList.contains('dreaming')) {
                whisperEl.textContent = 'drifting through collected moments...';
            } else {
                whisperEl.textContent = whispers[Math.floor(Math.random() * whispers.length)];
            }
        }, 15000);
    }

    // ==========================================
    // OBSERVATORY - SkyView Integration
    // ==========================================
    initObservatory() {
        this.observatoryImmersive = false;

        // Create immersive background container if it doesn't exist
        if (!document.getElementById('observatory-immersive-bg')) {
            const bg = document.createElement('div');
            bg.id = 'observatory-immersive-bg';
            bg.className = 'observatory-immersive-bg';
            bg.innerHTML = `
                <img id="starchart-bg-image" class="starchart-bg-image" alt="" />
                <div class="immersive-exit-zone" title="Click to exit immersive mode"></div>
            `;
            document.body.appendChild(bg);

            // Exit immersive mode on click
            bg.querySelector('.immersive-exit-zone').addEventListener('click', () => {
                this.toggleObservatoryImmersive(false);
            });
        }

        // Set up target buttons
        document.querySelectorAll('.sky-target-btn:not(.starchart-btn)').forEach(btn => {
            btn.addEventListener('click', () => this.loadSkyTarget(btn.dataset.target));
        });

        // Star chart button - now toggles immersive mode
        const starchartBtn = document.getElementById('load-starchart');
        if (starchartBtn) {
            starchartBtn.addEventListener('click', () => {
                this.loadStarChartBackground();
                this.toggleObservatoryImmersive(true);
            });
        }

        // Load initial random sky image for sidebar
        this.loadSkyTarget('random');

        // Load star chart as background
        this.loadStarChartBackground();

        // Load Astronomy API data
        this.loadAstronomyData();

        // Watch for theme changes to exit immersive mode
        this.watchObservatoryTheme();
    }

    toggleObservatoryImmersive(enable) {
        this.observatoryImmersive = enable;
        const bg = document.getElementById('observatory-immersive-bg');
        const hub = document.querySelector('.hub-container');

        if (enable) {
            bg?.classList.add('active');
            hub?.classList.add('observatory-immersive');
        } else {
            bg?.classList.remove('active');
            hub?.classList.remove('observatory-immersive');
        }
    }

    watchObservatoryTheme() {
        // Exit immersive mode when leaving observatory
        const hub = document.querySelector('.hub-container');
        if (!hub) return;

        const observer = new MutationObserver(() => {
            if (hub.dataset.theme !== 'observatory' && this.observatoryImmersive) {
                this.toggleObservatoryImmersive(false);
            }
        });

        observer.observe(hub, { attributes: true, attributeFilter: ['data-theme'] });
    }

    async loadStarChartBackground() {
        const bgImage = document.getElementById('starchart-bg-image');
        if (!bgImage) return;

        try {
            const response = await fetch(`${CONFIG.API_URL}/observatory/starchart`);
            const data = await response.json();

            if (data.imageUrl) {
                bgImage.src = data.imageUrl;
                console.log('[Observatory] Star chart background loaded');
            }
        } catch (error) {
            console.log('[Observatory] Star chart background unavailable:', error.message);
        }
    }

    async loadAstronomyData() {
        // Load moon phase
        this.loadMoonPhase();
        // Load planet positions
        this.loadPlanets();
        // Load tonight summary
        this.loadWhatsUp();
        // Load hometown weather
        this.loadHometownWeather();
    }

    async loadHometownWeather() {
        const statusEl = document.getElementById('weather-status');
        const cityEl = document.getElementById('hometown-city');
        const iconEl = document.getElementById('weather-icon');
        const tempEl = document.getElementById('weather-temp');
        const descEl = document.getElementById('weather-desc');
        const humidityEl = document.getElementById('weather-humidity');
        const windEl = document.getElementById('weather-wind');

        try {
            const response = await fetch(`${CONFIG.API_URL}/observatory/hometown-weather`);
            const data = await response.json();

            if (cityEl) {
                cityEl.textContent = `${data.city}, ${data.state}`;
            }

            if (data.error || !data.weather) {
                if (statusEl) statusEl.classList.remove('online');
                if (descEl) descEl.textContent = data.error || 'Weather unavailable';
                if (tempEl) tempEl.textContent = '--°F';
                return;
            }

            if (statusEl) statusEl.classList.add('online');

            const weather = data.weather;
            if (iconEl && weather.icon_url) {
                iconEl.src = weather.icon_url;
                iconEl.alt = weather.description;
            }
            if (tempEl) tempEl.textContent = `${weather.temp}°F`;
            if (descEl) descEl.textContent = weather.description;
            if (humidityEl) humidityEl.textContent = `${weather.humidity}% humidity`;
            if (windEl) windEl.textContent = `${weather.wind_speed} mph wind`;

        } catch (error) {
            console.error('[Observatory] Weather error:', error);
            if (statusEl) statusEl.classList.remove('online');
            if (descEl) descEl.textContent = 'Connection failed';
        }
    }

    async loadMoonPhase() {
        // Left sidebar elements
        const statusEl = document.getElementById('moon-status');
        const iconEl = document.getElementById('moon-phase-icon');
        const nameEl = document.getElementById('moon-phase-name');
        const constEl = document.getElementById('moon-constellation');
        // Right sidebar elements
        const statusElR = document.getElementById('moon-status-right');
        const iconElR = document.getElementById('moon-phase-icon-right');
        const nameElR = document.getElementById('moon-phase-name-right');
        const constElR = document.getElementById('moon-constellation-right');

        try {
            const response = await fetch(`${CONFIG.API_URL}/observatory/moon`);
            const data = await response.json();

            if (data.error) {
                if (statusEl) statusEl.classList.remove('online');
                if (nameEl) nameEl.textContent = 'OFFLINE';
                return;
            }

            if (statusEl) statusEl.classList.add('online');
            if (statusElR) statusElR.classList.add('online');

            // Moon phase emoji mapping
            const phaseIcons = {
                'New Moon': '🌑',
                'Waxing Crescent': '🌒',
                'First Quarter': '🌓',
                'Waxing Gibbous': '🌔',
                'Full Moon': '🌕',
                'Waning Gibbous': '🌖',
                'Last Quarter': '🌗',
                'Waning Crescent': '🌘'
            };

            const phaseName = data.phase?.string || 'Unknown';
            const icon = phaseIcons[phaseName] || '🌙';
            const name = phaseName.toUpperCase();
            const constellation = data.constellation ? `in ${data.constellation}` : '';
            // Update left sidebar
            if (iconEl) iconEl.textContent = icon;
            if (nameEl) nameEl.textContent = name;
            if (constEl) constEl.textContent = constellation;
            // Update right sidebar
            if (iconElR) iconElR.textContent = icon;
            if (nameElR) nameElR.textContent = name;
            if (constElR) constElR.textContent = constellation;

        } catch (error) {
            console.log('[Observatory] Moon API offline');
            if (statusEl) statusEl.classList.remove('online');
            if (statusElR) statusElR.classList.remove('online');
            if (nameEl) nameEl.textContent = 'OFFLINE';
            if (nameElR) nameElR.textContent = 'OFFLINE';
        }
    }

    async loadPlanets() {
        const statusEl = document.getElementById('planets-status');
        const listEl = document.getElementById('planets-list');
        // Right sidebar elements
        const statusElR = document.getElementById('planets-status-right');
        const listElR = document.getElementById('planets-list-right');

        try {
            const response = await fetch(`${CONFIG.API_URL}/observatory/planets`);
            const data = await response.json();

            if (data.error) {
                if (statusEl) statusEl.classList.remove('online');
                if (statusElR) statusElR.classList.remove('online');
                return;
            }

            if (statusEl) statusEl.classList.add('online');
            if (statusElR) statusElR.classList.add('online');

            if (data.planets) {
                const html = data.planets.map(planet => `
                    <div class="planet-item ${planet.visible ? 'visible' : ''}">
                        <span class="planet-name">${planet.name.toUpperCase()}</span>
                        <span class="planet-visibility">${planet.visible ? 'VISIBLE' : 'BELOW HORIZON'}</span>
                    </div>
                `).join('');
                if (listEl) listEl.innerHTML = html;
                if (listElR) listElR.innerHTML = html;
            }

        } catch (error) {
            console.log('[Observatory] Planets API offline');
            if (statusEl) statusEl.classList.remove('online');
            if (statusElR) statusElR.classList.remove('online');
        }
    }

    async loadWhatsUp() {
        const statusEl = document.getElementById('tonight-status');
        const summaryEl = document.getElementById('tonight-summary');

        try {
            const response = await fetch(`${CONFIG.API_URL}/observatory/whatsup`);
            const data = await response.json();

            if (data.error || (!data.moon && data.planet_count === 0)) {
                if (statusEl) statusEl.classList.remove('online');
                if (summaryEl) summaryEl.textContent = 'Astronomy API offline';
                return;
            }

            if (statusEl) statusEl.classList.add('online');
            if (summaryEl) summaryEl.textContent = data.summary || 'Looking up...';

        } catch (error) {
            console.log('[Observatory] WhatsUp API offline');
            if (statusEl) statusEl.classList.remove('online');
            if (summaryEl) summaryEl.textContent = 'Astronomy API offline';
        }
    }

    async loadStarChart() {
        const imageEl = document.getElementById('skyview-image');
        const nameEl = document.getElementById('skyview-name');
        const loadingEl = document.querySelector('.skyview-loading');

        if (loadingEl) loadingEl.style.display = 'block';
        if (loadingEl) loadingEl.textContent = 'Rendering star chart...';
        if (imageEl) imageEl.style.opacity = '0.3';

        try {
            const response = await fetch(`${CONFIG.API_URL}/observatory/starchart`);
            const data = await response.json();

            if (data.error) {
                if (loadingEl) loadingEl.textContent = 'Star chart API offline';
                return;
            }

            if (imageEl && data.imageUrl) {
                imageEl.src = data.imageUrl;
                imageEl.onload = () => {
                    imageEl.style.opacity = '1';
                    if (loadingEl) loadingEl.style.display = 'none';
                };
            }

            if (nameEl) nameEl.textContent = 'STAR CHART - Current Sky';

        } catch (error) {
            console.error('[Observatory] Star chart error:', error);
            if (loadingEl) loadingEl.textContent = 'Star chart unavailable';
        }
    }

    async loadSkyTarget(target) {
        const imageEl = document.getElementById('skyview-image');
        const nameEl = document.getElementById('skyview-name');
        const loadingEl = document.querySelector('.skyview-loading');

        if (loadingEl) loadingEl.style.display = 'block';
        if (imageEl) imageEl.style.opacity = '0.3';

        try {
            const endpoint = target === 'random'
                ? `${CONFIG.API_URL}/observatory/random`
                : `${CONFIG.API_URL}/observatory/skyview?target=${target}`;

            const response = await fetch(endpoint);
            const data = await response.json();

            if (imageEl) {
                imageEl.src = data.url;
                imageEl.onload = () => {
                    imageEl.style.opacity = '1';
                    if (loadingEl) loadingEl.style.display = 'none';
                };
                imageEl.onerror = () => {
                    if (loadingEl) loadingEl.textContent = 'Signal lost...';
                };
            }

            if (nameEl) {
                nameEl.textContent = data.name;
            }

            // Update active button
            document.querySelectorAll('.sky-target-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.target === target);
            });

        } catch (error) {
            console.error('[Observatory] Error loading sky image:', error);
            if (loadingEl) loadingEl.textContent = 'Connection to SkyView lost...';
        }
    }

    // ==========================================
    // CREW LOCATIONS
    // ==========================================
    initCrewLocations() {
        // Update locations on load
        this.updateCrewLocations();
        // Poll every 30 seconds
        setInterval(() => this.updateCrewLocations(), 30000);
    }

    async updateCrewLocations() {
        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/locations`);
            const data = await response.json();
            const locations = data.locations || data; // Handle both response formats

            // Clear all in-room indicators first (prevents stale glows on room change)
            document.querySelectorAll('.loc-indicator.in-room').forEach(el => {
                el.classList.remove('in-room');
            });

            // Get current room Casey is in
            const currentSection = document.querySelector('.sidebar-section.active')?.dataset.section;
            console.log('[Comms] Current section:', currentSection);

            // Map locations to sections for presence detection
            const locationToSection = {
                'bridge': 'claude',
                'claude': 'claude',
                'engineering': 'servers',
                'server': 'servers',
                'servers': 'servers',
                'ready_room': 'personal',
                'personal': 'personal',
                'science_lab': 'science',
                'science': 'science',
                'holodeck': 'games',
                'games': 'games',
                'messhall': 'messhall',
                'mess_hall': 'messhall',
                'medbay': 'med',
                'med': 'med',
                'rec_room': 'rec',
                'rec': 'rec',
                'observatory': 'observatory',
                'quarters': 'captains',
                'captains': 'captains',
                'corridor': 'corridor'
            };

            // Map crew IDs to their home/duty station locations
            // Location values match terminal IDs (claude, server, etc)
            const homeLocations = {
                'claude': 'claude',
                'server': 'server',
                'personal': 'personal',
                'science': 'science',
                'games': 'games',
                'med': 'med',
                'rec': 'rec'
            };

            for (const [crewId, locData] of Object.entries(locations)) {
                // Update ALL location list items for this crew (may be multiple)
                const items = document.querySelectorAll(`.crew-loc-item[data-crew="${crewId}"]`);
                items.forEach(item => {
                    const whereEl = item.querySelector('.loc-where');
                    if (whereEl) {
                        whereEl.textContent = locData.location_name;
                        whereEl.title = locData.activity || '';
                    }
                    const indicator = item.querySelector('.loc-indicator');
                    if (indicator) {
                        // Remove all location classes but keep base class
                        indicator.className = 'loc-indicator';

                        // Add location color class
                        const locationClass = (locData.location || '').replace('_', '-');
                        if (locationClass) {
                            indicator.classList.add(locationClass);
                        }

                        // Light up if crew is in the same room as Casey
                        const crewSection = locationToSection[locData.location] || locData.location;
                        const inRoom = (crewSection === currentSection);

                        if (inRoom) {
                            indicator.classList.add('in-room');
                        }

                        // Solid when at home/duty station, hollow when roaming
                        const homeLocation = homeLocations[crewId];
                        const atPost = locData.location === homeLocation;
                        indicator.classList.toggle('at-post', atPost);
                    }
                });

                // Log once per crew
                const crewSection = locationToSection[locData.location] || locData.location;
                const inRoom = (crewSection === currentSection);
                console.log(`[Comms] ${crewId}: location="${locData.location}" section="${crewSection}" current="${currentSection}" inRoom=${inRoom}`);

                // Special handling for Lumen's command card on bridge
                if (crewId === 'claude') {
                    const commandStatus = document.querySelector('.command-status');
                    if (commandStatus) {
                        const locationText = locData.location === 'claude' ? 'On the Bridge' : `@ ${locData.location_name}`;
                        commandStatus.textContent = locationText;
                    }
                }

                // Update terminal "away" status
                const terminal = document.getElementById(`terminal-${crewId}`);
                if (terminal) {
                    const isHome = locData.location === homeLocations[crewId];
                    const statusText = terminal.querySelector('.status-text');

                    if (!isHome) {
                        terminal.classList.add('crew-away');
                        if (statusText && !statusText.dataset.originalText) {
                            statusText.dataset.originalText = statusText.textContent;
                        }
                        if (statusText) {
                            statusText.textContent = `@ ${locData.location_name}`;
                        }
                    } else {
                        terminal.classList.remove('crew-away');
                        if (statusText && statusText.dataset.originalText) {
                            statusText.textContent = statusText.dataset.originalText;
                        }
                    }
                }
            }
        } catch (error) {
            // Silent fail - backend might not be up
        }
    }

    // ==========================================
    // CREW COMPLEMENT - They Matter
    // ==========================================
    initCrewComplement() {
        // Update complement on load
        this.updateCrewComplement();
        // Poll every 60 seconds
        setInterval(() => this.updateCrewComplement(), 60000);
    }

    async updateCrewComplement() {
        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/complement`);
            const data = await response.json();

            // Update display
            const totalEl = document.getElementById('complement-total');
            const namedEl = document.getElementById('named-count');
            const backgroundEl = document.getElementById('background-count');
            const interactionsEl = document.getElementById('interactions-count');

            if (totalEl) totalEl.textContent = data.complement || 7;
            if (namedEl) namedEl.textContent = data.named_crew_count || 7;
            if (backgroundEl) backgroundEl.textContent = data.background_crew_count || 0;
            if (interactionsEl) interactionsEl.textContent = data.interactions_7day || 0;

            // Update status indicator
            const statusEl = document.getElementById('complement-status');
            if (statusEl) {
                statusEl.classList.add('online');
            }

        } catch (error) {
            console.log('[Complement] Could not fetch crew complement:', error.message);
        }
    }

    // ==========================================
    // LIGHTS OUT - CREW REFLECTION
    // ==========================================
    initLightsOut() {
        const triggerBtn = document.getElementById('begin-reflection');
        const statusDiv = document.getElementById('reflection-status');

        if (triggerBtn) {
            triggerBtn.addEventListener('click', () => this.beginReflection());
        }

        // Power button on Bridge sidebar - make draggable
        const powerBtn = document.getElementById('lights-out-power-btn');
        const powerContainer = powerBtn?.closest('.lights-out-power');

        if (powerBtn && powerContainer) {
            const POWER_POS_KEY = 'claude-hub-power-btn-position';
            let isDragging = false;
            let dragStarted = false;
            let startX, startY, btnX, btnY;

            // Load saved position
            const saved = localStorage.getItem(POWER_POS_KEY);
            if (saved) {
                try {
                    const pos = JSON.parse(saved);
                    powerContainer.style.position = 'fixed';
                    powerContainer.style.left = Math.min(Math.max(0, pos.x), window.innerWidth - 60) + 'px';
                    powerContainer.style.top = Math.min(Math.max(0, pos.y), window.innerHeight - 60) + 'px';
                    powerContainer.style.right = 'auto';
                    powerContainer.style.bottom = 'auto';
                    powerContainer.style.margin = '0';
                    powerContainer.style.padding = '0';
                    powerContainer.style.zIndex = '100';
                } catch (e) {}
            }

            powerBtn.addEventListener('mousedown', (e) => {
                startX = e.clientX;
                startY = e.clientY;
                const rect = powerContainer.getBoundingClientRect();
                btnX = rect.left;
                btnY = rect.top;
                dragStarted = false;

                document.addEventListener('mousemove', onDrag);
                document.addEventListener('mouseup', onDragEnd);
            });

            function onDrag(e) {
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;

                if (!dragStarted && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
                    dragStarted = true;
                    isDragging = true;
                    powerContainer.style.position = 'fixed';
                    powerContainer.style.right = 'auto';
                    powerContainer.style.bottom = 'auto';
                    powerContainer.style.margin = '0';
                    powerContainer.style.padding = '0';
                    powerContainer.style.zIndex = '100';
                }

                if (isDragging) {
                    const newX = Math.min(Math.max(0, btnX + dx), window.innerWidth - 60);
                    const newY = Math.min(Math.max(0, btnY + dy), window.innerHeight - 60);
                    powerContainer.style.left = newX + 'px';
                    powerContainer.style.top = newY + 'px';
                }
            }

            function onDragEnd() {
                document.removeEventListener('mousemove', onDrag);
                document.removeEventListener('mouseup', onDragEnd);

                if (isDragging) {
                    const rect = powerContainer.getBoundingClientRect();
                    localStorage.setItem(POWER_POS_KEY, JSON.stringify({ x: rect.left, y: rect.top }));
                    isDragging = false;
                    dragStarted = false;
                } else if (!dragStarted) {
                    // Was a click, not a drag - navigate to lights out
                    const lightsOutNav = document.querySelector('.nav-btn[data-section="lightsout"]');
                    if (lightsOutNav) {
                        lightsOutNav.click();
                    }
                    if (window.soundSystem) {
                        window.soundSystem.playChirp();
                    }
                }
                dragStarted = false;
            }
        }
    }

    async beginReflection() {
        const triggerBtn = document.getElementById('begin-reflection');
        const statusDiv = document.getElementById('reflection-status');
        const crewItems = document.querySelectorAll('.crew-reflect-item');

        // Disable button
        if (triggerBtn) {
            triggerBtn.disabled = true;
            triggerBtn.textContent = 'REFLECTING...';
        }

        // Update status
        if (statusDiv) {
            statusDiv.innerHTML = '<p class="reflecting">The crew grows quiet, each alone with their thoughts...</p>';
        }

        // Mark all crew as reflecting
        crewItems.forEach(item => {
            const status = item.querySelector('.reflect-status');
            if (status) status.textContent = 'reflecting...';
            item.classList.add('reflecting');
        });

        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/reflect-all`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();
            console.log('[Lights Out] Reflection results:', data);

            // Update each crew member's status
            for (const [crewId, result] of Object.entries(data.results || {})) {
                const item = document.querySelector(`.crew-reflect-item[data-crew="${crewId}"]`);
                if (item) {
                    item.classList.remove('reflecting');
                    const status = item.querySelector('.reflect-status');
                    if (result.action === 'keep') {
                        item.classList.add('kept');
                        if (status) status.textContent = 'unchanged';
                    } else if (result.action === 'rewrite') {
                        item.classList.add('changed');
                        if (status) status.textContent = 'evolved';
                    } else {
                        if (status) status.textContent = 'error';
                    }
                }
            }

            // Update status message
            if (statusDiv) {
                const changed = Object.values(data.results || {}).filter(r => r.action === 'rewrite').length;
                const kept = Object.values(data.results || {}).filter(r => r.action === 'keep').length;
                statusDiv.innerHTML = `<p class="complete">Reflection complete. ${changed} evolved, ${kept} remained.</p>`;
            }

            // Show toast
            if (window.ambientSystem) {
                window.ambientSystem.showToast('Lights out reflection complete');
            }

        } catch (error) {
            console.error('[Lights Out] Error:', error);
            if (statusDiv) {
                statusDiv.innerHTML = '<p class="error">Reflection interrupted. The ship stirs...</p>';
            }
        }

        // Re-enable button
        if (triggerBtn) {
            triggerBtn.disabled = false;
            triggerBtn.textContent = 'BEGIN REFLECTION';
        }
    }

    // ==========================================
    // BACKEND STATUS CHECK
    // ==========================================
    async checkBackendStatus() {
        try {
            const response = await fetch(`${CONFIG.API_URL}/health`);
            if (response.ok) {
                console.log('Backend connected');
                this.setBackendStatus(true);
            }
        } catch {
            console.log('Backend not available - running in demo mode');
            this.setBackendStatus(false);
        }
    }

    setBackendStatus(connected) {
        const indicator = document.querySelector('.panel-indicator.online');
        if (indicator && !connected) {
            indicator.classList.remove('online');
        }
    }

    // ==========================================
    // FOCUS MODE
    // ==========================================
    toggleFocusMode() {
        document.body.classList.toggle('focus-mode');

        if (window.ambientSystem) {
            const isFocused = document.body.classList.contains('focus-mode');
            window.ambientSystem.showToast(isFocused ? 'Focus mode ON' : 'Focus mode OFF');
        }
    }

    // ==========================================
    // API
    // ==========================================
    getStatus() {
        return {
            version: this.version,
            initialized: this.initialized,
            terminals: window.terminalManager?.terminals.size || 0,
            soundEnabled: window.soundSystem?.enabled || false
        };
    }
}

// ==========================================
// GLOBAL KEYBOARD SHORTCUTS
// ==========================================
document.addEventListener('keydown', (e) => {
    // F11 for native fullscreen
    if (e.key === 'F11') {
        e.preventDefault();
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                console.log('Fullscreen not available:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }

    // Ctrl+Shift+F for focus mode (hides UI elements)
    if (e.ctrlKey && e.shiftKey && e.key === 'F') {
        e.preventDefault();
        if (window.claudeHub) {
            window.claudeHub.toggleFocusMode();
        }
    }

    // Ctrl+Shift+S for sound toggle
    if (e.ctrlKey && e.shiftKey && e.key === 'S') {
        e.preventDefault();
        if (window.soundSystem) {
            const enabled = window.soundSystem.toggle();
            if (window.ambientSystem) {
                window.ambientSystem.showToast(enabled ? 'Sound ON' : 'Sound OFF');
            }
        }
    }
});

// ==========================================
// PREVENT CONTEXT MENU ON TERMINALS
// ==========================================
document.addEventListener('contextmenu', (e) => {
    if (e.target.closest('.terminal-panel')) {
        e.preventDefault();
    }
});

// ==========================================
// INITIALIZE
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    window.claudeHub = new ClaudeHub();

    // Easter egg
    console.log('%c🖖 Live long and prosper.', 'color: #cc99ff; font-size: 14px;');
});

// ==========================================
// LOADING ANIMATION
// ==========================================
window.addEventListener('load', () => {
    document.body.classList.add('loaded');

    // Remove any loading overlays
    const loader = document.getElementById('loader');
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => loader.remove(), 500);
    }
});

// ==========================================
// SCIENCE LAB - Project Stats
// ==========================================

async function loadProjectStats() {
    try {
        const response = await fetch('/projects/stats');
        const stats = await response.json();
        
        document.getElementById('stat-total').textContent = stats.total || 0;
        document.getElementById('stat-active').textContent = stats.by_status?.active || 0;
        document.getElementById('stat-priority').textContent = stats.by_priority?.high || 0;
        document.getElementById('stat-mystery').textContent = stats.by_status?.mystery || 0;
        
        // Load high priority active projects
        if (stats.high_priority_active && stats.high_priority_active.length > 0) {
            const activeList = document.getElementById('active-projects');
            activeList.innerHTML = stats.high_priority_active
                .map(name => `<div class="project-item high-priority">${name}</div>`)
                .join('');
        }
        
        // Load projects needing attention (mystery status)
        const projectsResponse = await fetch('/projects?status=mystery');
        const projectsData = await projectsResponse.json();
        if (projectsData.projects && projectsData.projects.length > 0) {
            const attentionList = document.getElementById('attention-projects');
            attentionList.innerHTML = projectsData.projects
                .map(p => `<div class="project-item">${p.name}</div>`)
                .join('');
        }
    } catch (e) {
        console.error('[Science] Failed to load project stats:', e);
    }
}

// Load stats when Science section is shown
document.querySelectorAll('.nav-btn[data-section="science"]').forEach(btn => {
    btn.addEventListener('click', () => {
        loadProjectStats();
    });
});

// Initial load if Science section exists
if (document.querySelector('[data-section="science"]')) {
    loadProjectStats();

    // Initialize autonomy settings
    initAutonomySettings();
}

// ==========================================
// AUTONOMY SETTINGS
// ==========================================

let autonomyStatus = { enabled: false, tick_rate: 30 };

async function initAutonomySettings() {
    const rateSelect = document.getElementById('autonomy-rate');
    const pauseBtn = document.getElementById('autonomy-pause');
    const triggerBtn = document.getElementById('autonomy-trigger');
    const statusEl = document.getElementById('autonomy-status');

    if (!rateSelect || !pauseBtn || !triggerBtn || !statusEl) return;

    // Load current status
    await updateAutonomyStatus();

    // Tick rate change
    rateSelect.addEventListener('change', async () => {
        const newRate = parseInt(rateSelect.value);
        try {
            const response = await fetch(`${CONFIG.API_URL}/autonomy/tick-rate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tick_rate: newRate })
            });
            if (response.ok) {
                autonomyStatus.tick_rate = newRate;
                console.log(`[Autonomy] Tick rate set to ${newRate}s`);
            }
        } catch (err) {
            console.error('[Autonomy] Failed to set tick rate:', err);
        }
    });

    // Pause/Resume toggle
    pauseBtn.addEventListener('click', async () => {
        const newState = !autonomyStatus.enabled;
        try {
            const endpoint = newState ? '/autonomy/enable' : '/autonomy/disable';
            const response = await fetch(`${CONFIG.API_URL}${endpoint}`, {
                method: 'POST'
            });
            if (response.ok) {
                autonomyStatus.enabled = newState;
                updateAutonomyUI();
                console.log(`[Autonomy] ${newState ? 'Enabled' : 'Disabled'}`);
            }
        } catch (err) {
            console.error('[Autonomy] Failed to toggle:', err);
        }
    });

    // Trigger now
    triggerBtn.addEventListener('click', async () => {
        try {
            triggerBtn.disabled = true;
            triggerBtn.textContent = 'TRIGGERING...';

            const response = await fetch(`${CONFIG.API_URL}/autonomy/tick`, {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                console.log('[Autonomy] Manual tick completed:', result);

                triggerBtn.textContent = 'DONE!';
                setTimeout(() => {
                    triggerBtn.textContent = 'TRIGGER NOW';
                    triggerBtn.disabled = false;
                }, 2000);
            }
        } catch (err) {
            console.error('[Autonomy] Failed to trigger:', err);
            triggerBtn.textContent = 'TRIGGER NOW';
            triggerBtn.disabled = false;
        }
    });

    // Poll status every 10 seconds
    setInterval(updateAutonomyStatus, 10000);
}

async function updateAutonomyStatus() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/autonomy/status`);
        if (response.ok) {
            const data = await response.json();
            autonomyStatus.enabled = data.enabled || false;
            autonomyStatus.tick_rate = data.tick_rate || 30;
            autonomyStatus.tick_count = data.tick_count || 0;
            autonomyStatus.last_tick = data.last_tick;

            updateAutonomyUI();
        }
    } catch (err) {
        // Backend might not be running
    }
}

function updateAutonomyUI() {
    const rateSelect = document.getElementById('autonomy-rate');
    const pauseBtn = document.getElementById('autonomy-pause');
    const statusEl = document.getElementById('autonomy-status');

    if (!statusEl) return;

    // Update status indicator
    const statusClass = autonomyStatus.enabled ? 'online' : 'offline';
    const statusText = autonomyStatus.enabled
        ? `Active (${autonomyStatus.tick_count || 0} ticks)`
        : 'Paused';

    statusEl.className = `autonomy-status-value ${statusClass}`;
    statusEl.textContent = statusText;

    // Update button text
    if (pauseBtn) {
        pauseBtn.textContent = autonomyStatus.enabled ? 'PAUSE AUTONOMY' : 'RESUME AUTONOMY';
        pauseBtn.className = autonomyStatus.enabled ? 'settings-btn danger' : 'settings-btn primary';
    }

    // Update dropdown
    if (rateSelect && autonomyStatus.tick_rate) {
        rateSelect.value = autonomyStatus.tick_rate;
    }
}

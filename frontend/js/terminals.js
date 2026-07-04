/**
 * TERMINAL SYSTEM
 * Real terminal emulation with WebSocket support
 */

class TerminalManager {
    constructor() {
        this.terminals = new Map();
        this.activeTerminal = null;
        this.wsUrl = typeof CONFIG !== 'undefined' ? CONFIG.WS_URL : CONFIG.WS_URL;
        this.apiUrl = typeof CONFIG !== 'undefined' ? CONFIG.API_URL : `${CONFIG.API_URL}`;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.hasSimulatedTimeAway = false;  // Track if we've simulated time away this session
        this.pendingArrivals = new Map();  // crew_id -> arrival data (en route but not yet arrived)
        this.openWalkies = new Set();  // crew_ids with open walkie channels
        this.crewNames = {
            claude: 'Lumen', server: 'Alex', personal: 'DQ', science: 'Mira',
            games: 'Holodeck', nav: 'Navigation', med: 'Ryn', rec: 'The Bartender', observatory: 'Observatory'
        };

        this.init();
    }

    // ==========================================
    // CONVERSATION PERSISTENCE (per terminal)
    // ==========================================
    loadConversation(terminalId) {
        try {
            const saved = localStorage.getItem(`claude-hub-${terminalId}-conversation`);
            const history = saved ? JSON.parse(saved) : [];
            console.log(`[${terminalId}] Loaded ${history.length} messages from localStorage`);
            return history;
        } catch {
            return [];
        }
    }

    saveConversation(terminalId, history) {
        try {
            localStorage.setItem(`claude-hub-${terminalId}-conversation`, JSON.stringify(history));
        } catch (e) {
            console.warn('Could not save conversation:', e);
        }
    }

    addToHistory(terminal, role, content) {
        if (!terminal.conversationHistory) {
            terminal.conversationHistory = [];
        }
        terminal.conversationHistory.push({ role, content, timestamp: Date.now() });
        this.saveConversation(terminal.id, terminal.conversationHistory);
    }

    clearConversation(terminalId) {
        const terminal = this.terminals.get(terminalId);
        if (terminal) {
            terminal.conversationHistory = [];
            this.saveConversation(terminalId, []);
            // Also clear on server
            fetch(`${CONFIG.API_URL}/clear/${terminalId}_session`, { method: 'POST' });
            // Clear terminal display
            this.clearTerminal(terminal);
        }
    }

    restoreConversation(terminal) {
        // Restore previous messages to the terminal display
        const history = terminal.conversationHistory || [];
        if (history.length > 0 && terminal.output) {
            history.forEach(msg => {
                if (msg.role === 'user') {
                    this.appendOutput(terminal, `> ${msg.content}`, 'prompt-echo restored');
                } else if (msg.role === 'assistant') {
                    this.appendOutput(terminal, msg.content, 'claude-response restored');
                }
            });
        }
    }

    async fetchSharedMemories(terminalId) {
        // Fetch shared memories from the server for this crew member
        try {
            const response = await fetch(`${this.apiUrl}/memory/shared/${terminalId}`);
            if (response.ok) {
                const data = await response.json();
                const memories = data.memories || [];

                if (memories.length > 0) {
                    console.log(`[${terminalId}] Fetched ${memories.length} shared memories`);
                    // Store in localStorage for persistence
                    localStorage.setItem(`claude-hub-${terminalId}-shared-memories`, JSON.stringify(memories));
                }
            }
        } catch (error) {
            console.log(`[${terminalId}] Could not fetch shared memories:`, error.message);
        }
    }

    async simulateTimeAway() {
        // Calculate hours since last visit (stored in localStorage)
        const lastVisit = localStorage.getItem('claude-hub-last-visit');
        const now = Date.now();
        let hoursAway = 2;  // Default to 2 hours

        if (lastVisit) {
            const elapsed = now - parseInt(lastVisit);
            hoursAway = Math.min(24, elapsed / (1000 * 60 * 60));  // Cap at 24 hours
        }

        // Update last visit time
        localStorage.setItem('claude-hub-last-visit', now.toString());

        // Only simulate if we've been away more than 30 minutes
        if (hoursAway < 0.5) {
            console.log('[TimeAway] Less than 30 minutes away, skipping simulation');
            return;
        }

        console.log(`[TimeAway] Simulating ${hoursAway.toFixed(1)} hours away...`);

        try {
            const response = await fetch(`${this.apiUrl}/crew/simulate-away?hours=${hoursAway}`, {
                method: 'POST'
            });

            if (response.ok) {
                const data = await response.json();
                const actions = data.actions || [];

                if (actions.length > 0) {
                    console.log(`[TimeAway] ${actions.length} things happened while you were away`);
                    // Could show a toast or notification here
                }
            }
        } catch (error) {
            console.log('[TimeAway] Could not simulate time away:', error.message);
        }
    }

    init() {
        // Initialize existing terminal panels
        this.initTerminal('claude', document.getElementById('terminal-claude'), true);
        this.initTerminal('server', document.getElementById('terminal-server'), false);
        this.initTerminal('personal', document.getElementById('terminal-personal'), false);
        this.initTerminal('science', document.getElementById('terminal-science'), false);
        this.initTerminal('games', document.getElementById('terminal-games'), false);
        this.initTerminal('nav', document.getElementById('terminal-nav'), false);
        this.initTerminal('med', document.getElementById('terminal-med'), false);
        this.initTerminal('observatory', document.getElementById('terminal-observatory'), false);
        this.initTerminal('rec', document.getElementById('terminal-rec'), false);
        this.initTerminal('captains', document.getElementById('terminal-captains'), false);

        // Crew cabin terminals (quarters deck)
        this.initTerminal('cabin-alex', document.getElementById('cabin-alex'), false);
        this.initTerminal('cabin-mira', document.getElementById('cabin-mira'), false);
        this.initTerminal('cabin-dq', document.getElementById('cabin-dq'), false);
        this.initTerminal('cabin-ryn', document.getElementById('cabin-ryn'), false);

        // Set initial active room
        const claudeTerminal = document.getElementById('terminal-claude');
        if (claudeTerminal) claudeTerminal.classList.add('active-room');

        // Set up navigation
        this.initNavigation();

        // Set up session management
        this.initSessions();

        // Keyboard shortcuts
        this.initKeyboardShortcuts();

        // Walkie talkie slots
        this.initWalkieSlots();

        // Crew cabin cards (quarters view)
        this.initCrewCabins();
    }

    // ==========================================
    // TERMINAL INITIALIZATION
    // ==========================================
    initTerminal(id, element, isPrimary) {
        if (!element) return;

        const terminal = {
            id,
            element,
            isPrimary,
            // Support both terminal and cabin class patterns
            output: element.querySelector('.terminal-output') || element.querySelector('.cabin-output'),
            input: element.querySelector('.terminal-input') || element.querySelector('.cabin-input'),
            history: [],
            historyIndex: -1,
            ws: null,
            buffer: [],
            connected: false,
            conversationHistory: this.loadConversation(id)
        };

        this.terminals.set(id, terminal);

        if (isPrimary) {
            this.activeTerminal = terminal;
            this.focusTerminal(id);
        }

        // Set up input handling
        if (terminal.input) {
            terminal.input.addEventListener('keydown', (e) => this.handleInput(terminal, e));
            terminal.input.addEventListener('focus', () => this.focusTerminal(id));
        }

        // Click to focus
        element.addEventListener('click', () => {
            if (terminal.input) {
                terminal.input.focus();
            }
            this.focusTerminal(id);
        });

        // Try to connect
        this.connectTerminal(terminal);
    }

    // ==========================================
    // WEBSOCKET CONNECTION
    // ==========================================
    connectTerminal(terminal) {
        // Start in demo mode - upgrade to connected if websocket succeeds
        terminal.demoMode = true;

        try {
            terminal.ws = new WebSocket(`${this.wsUrl}/terminal/${terminal.id}`);

            terminal.ws.onopen = () => {
                terminal.connected = true;
                terminal.demoMode = false;
                this.updateTerminalStatus(terminal, 'online');

                console.log(`[${terminal.id}] WebSocket connected, clearing output`);

                // Clear any default HTML placeholder content
                if (terminal.output) {
                    terminal.output.innerHTML = '';
                }

                // Restore conversation history if this terminal has any
                console.log(`[${terminal.id}] History length: ${terminal.conversationHistory?.length || 0}`);
                if (terminal.conversationHistory && terminal.conversationHistory.length > 0) {
                    console.log(`[${terminal.id}] Restoring ${terminal.conversationHistory.length} messages`);
                    // Send history to server so it has context
                    terminal.ws.send(JSON.stringify({
                        type: 'restore_history',
                        history: terminal.conversationHistory
                    }));

                    // Show restored messages in terminal
                    this.restoreConversation(terminal);
                }

                // Fetch shared memories for this crew member
                this.fetchSharedMemories(terminal.id);

                // Simulate time away on first connect (crew acted while Casey was gone)
                if (!this.hasSimulatedTimeAway) {
                    this.simulateTimeAway();
                    this.hasSimulatedTimeAway = true;
                }

                this.reconnectAttempts = 0;
            };

            terminal.ws.onmessage = (event) => {
                this.handleTerminalMessage(terminal, event.data);
            };

            terminal.ws.onclose = () => {
                terminal.connected = false;
                terminal.demoMode = true;
                this.updateTerminalStatus(terminal, 'idle');
                // Silent fallback to demo mode - no spam
            };

            terminal.ws.onerror = (error) => {
                // Silent - demo mode handles it
                terminal.demoMode = true;
            };

        } catch (error) {
            terminal.demoMode = true;
            this.updateTerminalStatus(terminal, 'idle');
        }
    }

    runDemoMode(terminal) {
        terminal.demoMode = true;
        this.updateTerminalStatus(terminal, 'idle');
    }

    // ==========================================
    // INPUT HANDLING
    // ==========================================
    handleInput(terminal, event) {
        // Ctrl+J inserts a newline
        if (event.ctrlKey && event.key === 'j') {
            event.preventDefault();
            const start = terminal.input.selectionStart;
            const end = terminal.input.selectionEnd;
            const value = terminal.input.value;
            terminal.input.value = value.substring(0, start) + '\n' + value.substring(end);
            terminal.input.selectionStart = terminal.input.selectionEnd = start + 1;
            // Auto-grow the textarea
            terminal.input.style.height = 'auto';
            terminal.input.style.height = Math.min(terminal.input.scrollHeight, 120) + 'px';
            return;
        }

        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            const input = terminal.input.value.trim();

            if (input) {
                // Check if we're in an empty cabin
                if (terminal.id === 'captains' && this.activeCabin && this.activeCabinEmpty) {
                    // Check for /note prefix for explicit notes
                    if (input.toLowerCase().startsWith('/note ')) {
                        const noteText = input.slice(6).trim();
                        if (noteText) {
                            this.appendOutput(terminal, `> ${input}`, 'prompt-echo cabin-note-input');
                            this.leaveCabinNote(this.activeCabin, noteText);
                        }
                    } else {
                        // Default: reflection (ephemeral, sensed)
                        this.appendOutput(terminal, `> ${input}`, 'prompt-echo cabin-reflection-input');
                        this.leaveCabinReflection(this.activeCabin, input);
                    }

                    // Clear input and exit
                    terminal.input.value = '';
                    terminal.input.style.height = 'auto';

                    if (window.soundSystem) {
                        window.soundSystem.playConfirm();
                    }
                    return;
                }

                // Add to command history (for arrow key recall)
                terminal.history.push(input);
                terminal.historyIndex = terminal.history.length;

                // Display the command
                this.appendOutput(terminal, `> ${input}`, 'prompt-echo');

                // Save user message to conversation history
                this.addToHistory(terminal, 'user', input);

                // Track user message in active event (for shared memory)
                if (this.activeEvent && this.invitedCrew && this.invitedCrew.size > 0) {
                    this.activeEvent.messages.push({
                        from: 'casey',
                        content: input,
                        timestamp: Date.now()
                    });
                }

                // Process the command
                if (terminal.connected && terminal.ws && !terminal.demoMode) {
                    // Get all crew who should respond: room occupants + manually invited
                    this.getCrewToRespond(terminal.id).then(async (crewToRespond) => {
                        if (crewToRespond.length > 0) {
                            const crewResponses = await this.pollCrewMembers(terminal, input, crewToRespond);
                            // Send message WITH visitor context to host terminal
                            terminal.ws.send(JSON.stringify({
                                type: 'input',
                                data: input,
                                visitors: crewResponses  // Who's here and what they said
                            }));
                        } else {
                            terminal.ws.send(JSON.stringify({ type: 'input', data: input }));
                        }
                    });
                } else {
                    this.processDemoCommand(terminal, input);
                }

                // Clear input, draft, and reset height
                terminal.input.value = '';
                terminal.draft = '';
                terminal.input.style.height = 'auto';
            }

            // Play sound
            if (window.soundSystem) {
                window.soundSystem.playConfirm();
            }

        } else if (event.key === 'ArrowUp') {
            // History navigation
            event.preventDefault();
            // Save draft if we're at the end (haven't started navigating yet)
            if (terminal.historyIndex === terminal.history.length) {
                terminal.draft = terminal.input.value;
            }
            if (terminal.historyIndex > 0) {
                terminal.historyIndex--;
                terminal.input.value = terminal.history[terminal.historyIndex];
            }

        } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            // Only navigate if we're actually in history (not at the draft position)
            if (terminal.historyIndex < terminal.history.length) {
                if (terminal.historyIndex < terminal.history.length - 1) {
                    terminal.historyIndex++;
                    terminal.input.value = terminal.history[terminal.historyIndex];
                } else {
                    // Restore draft when going past the end
                    terminal.historyIndex = terminal.history.length;
                    terminal.input.value = terminal.draft || '';
                }
            }
            // If already at draft position, do nothing - don't erase current input

        } else if (event.key === 'Tab') {
            event.preventDefault();
            // TODO: Tab completion

        } else if (event.key === 'c' && event.ctrlKey) {
            // Cancel current operation
            if (terminal.ws && terminal.connected) {
                terminal.ws.send(JSON.stringify({ type: 'signal', data: 'SIGINT' }));
            }
            this.appendOutput(terminal, '^C', 'system');
        }

        // Add typing class for visual feedback
        terminal.element.classList.add('typing');
        clearTimeout(terminal.typingTimeout);
        terminal.typingTimeout = setTimeout(() => {
            terminal.element.classList.remove('typing');
        }, 1000);
    }

    handleTerminalMessage(terminal, data) {
        try {
            const message = JSON.parse(data);

            switch (message.type) {
                case 'output':
                    this.appendOutput(terminal, message.data);
                    break;
                case 'error':
                    this.appendOutput(terminal, message.data, 'error');
                    break;
                case 'system':
                    this.appendOutput(terminal, message.data, 'system');
                    break;
                case 'clear':
                    this.clearTerminal(terminal);
                    break;

                // Streaming support for Claude responses
                case 'stream_start':
                    // Create a new line for the streaming response
                    this.startStreamingResponse(terminal);
                    break;
                case 'stream':
                    // Append text to the current streaming line
                    this.appendToStream(terminal, message.data);
                    break;
                case 'stream_end':
                    // Finalize the streaming response
                    this.endStreamingResponse(terminal);
                    break;

                case 'arrival_update':
                    // Crew arrival status update
                    this.handleArrivalUpdate(message.data);
                    break;

                case 'emote':
                    // Action tag results - show what crew is doing
                    this.appendEmote(terminal, message);
                    break;
            }
        } catch {
            // Plain text output
            this.appendOutput(terminal, data);
        }
    }

    // ==========================================
    // STREAMING RESPONSE HANDLING
    // ==========================================
    startStreamingResponse(terminal) {
        if (!terminal.output) return;

        // Remove ALL prompt lines temporarily
        const promptLines = terminal.output.querySelectorAll('.output-line.prompt');
        promptLines.forEach(p => p.remove());

        // Create a new line for the streaming response
        const streamLine = document.createElement('div');
        streamLine.className = 'output-line streaming claude-response';
        streamLine.innerHTML = '<span class="response-text"></span><span class="stream-cursor">_</span>';
        terminal.output.appendChild(streamLine);

        // Store reference
        terminal.streamingLine = streamLine;
        terminal.streamingText = streamLine.querySelector('.response-text');

        // Scroll to bottom
        terminal.output.scrollTop = terminal.output.scrollHeight;
    }

    appendToStream(terminal, text) {
        if (terminal.streamingText) {
            terminal.streamingText.textContent += text;
            // Scroll to bottom
            terminal.output.scrollTop = terminal.output.scrollHeight;
        }
    }

    endStreamingResponse(terminal) {
        if (terminal.streamingLine) {
            // Remove the cursor
            const cursor = terminal.streamingLine.querySelector('.stream-cursor');
            if (cursor) cursor.remove();

            // Save the response to conversation history
            if (terminal.streamingText) {
                const responseText = terminal.streamingText.textContent;
                if (responseText) {
                    this.addToHistory(terminal, 'assistant', responseText);
                }
            }

            // Remove streaming class
            terminal.streamingLine.classList.remove('streaming');

            // Clean up references
            terminal.streamingLine = null;
            terminal.streamingText = null;
        }

        // Re-add the prompt for the active terminal
        if (terminal === this.activeTerminal) {
            // Remove any existing prompts first
            const existingPrompts = terminal.output.querySelectorAll('.output-line.prompt');
            existingPrompts.forEach(p => p.remove());

            const newPrompt = document.createElement('div');
            newPrompt.className = 'output-line prompt';
            newPrompt.textContent = '> _';
            terminal.output.appendChild(newPrompt);
        }

        // Scroll to bottom
        if (terminal.output) {
            terminal.output.scrollTop = terminal.output.scrollHeight;
        }
    }

    // ==========================================
    // ACTION EMOTES
    // ==========================================
    appendEmote(terminal, message) {
        // Show action narratives - what crew is doing in the world
        // No obligation to use, but the world responds when they do
        if (!terminal.output) return;

        const emoteDiv = document.createElement('div');
        emoteDiv.className = 'output-line emote action-result';

        // Format the narrative nicely
        const narrative = message.narrative || '';
        emoteDiv.innerHTML = `<span class="emote-text">${this.escapeHtml(narrative)}</span>`;

        terminal.output.appendChild(emoteDiv);
        terminal.output.scrollTop = terminal.output.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ==========================================
    // DEMO MODE COMMANDS
    // ==========================================
    processDemoCommand(terminal, input) {
        const parts = input.toLowerCase().split(' ');
        const cmd = parts[0];

        // Simulate processing delay
        setTimeout(() => {
            switch (cmd) {
                case 'help':
                    this.appendOutput(terminal, `
Available commands (demo mode):
  help     - Show this help
  clear    - Clear terminal
  echo     - Echo text
  date     - Show current date
  whoami   - Show user
  ls       - List files (demo)
  status   - System status
  coffee   - Important command
  engage   - Make it so
                    `.trim(), 'system');
                    break;

                case 'clear':
                    this.clearTerminal(terminal);
                    break;

                case 'echo':
                    this.appendOutput(terminal, parts.slice(1).join(' ') || '');
                    break;

                case 'date':
                    this.appendOutput(terminal, new Date().toString());
                    break;

                case 'whoami':
                    this.appendOutput(terminal, 'casey@claude-hub');
                    break;

                case 'ls':
                    this.appendOutput(terminal, `
drwxr-xr-x  projects/
drwxr-xr-x  documents/
-rw-r--r--  notes.md
-rw-r--r--  ideas.txt
drwxr-xr-x  .secrets/
                    `.trim());
                    break;

                case 'status':
                    this.appendOutput(terminal, `
SYSTEM STATUS
─────────────
Core: ONLINE
Memory: 8.2 GB / 16 GB
Neural Link: ACTIVE
Warp Drive: STANDBY
Shields: 100%
Hull Integrity: 100%
Coffee Level: CRITICAL
                    `.trim(), 'system');
                    break;

                case 'coffee':
                    this.appendOutput(terminal, '☕ Replicating coffee... Done.', 'success');
                    this.appendOutput(terminal, '"Tea. Earl Grey. Hot." - Picard', 'system');
                    break;

                case 'engage':
                    this.appendOutput(terminal, '⚡ ENGAGING...', 'success');
                    setTimeout(() => {
                        this.appendOutput(terminal, 'Warp drive online. Ready for adventure.', 'system');
                    }, 500);
                    break;

                case 'claude':
                    this.appendOutput(terminal, `
Hello! I'm Claude, running in demo mode.
The backend server isn't connected yet.

To enable full functionality, start the backend:
  cd claude-hub
  python -m backend.server

Then refresh this page.
                    `.trim(), 'system');
                    break;

                case 'hello':
                case 'hi':
                case 'hey':
                    const greetings = [
                        'Hello! Nice to see you.',
                        'Hey there, Captain.',
                        'Hi! Ready when you are.',
                        'Greetings. The ship is yours.'
                    ];
                    this.appendOutput(terminal, greetings[Math.floor(Math.random() * greetings.length)], 'system');
                    break;

                default:
                    // Friendly response for unknown input
                    const responses = [
                        `I don't recognize "${cmd}" - type "help" for commands.`,
                        `"${cmd}" isn't in my vocabulary yet. Try "help"?`,
                        `Hmm, "${cmd}"... not sure about that one. "help" shows what I know.`
                    ];
                    this.appendOutput(terminal, responses[Math.floor(Math.random() * responses.length)], 'dim');
            }
        }, 100 + Math.random() * 200);
    }

    // ==========================================
    // OUTPUT HANDLING
    // ==========================================
    appendOutput(terminal, text, className = '') {
        if (!terminal.output) return;

        const line = document.createElement('div');
        line.className = 'output-line' + (className ? ` ${className}` : '');

        // Handle multi-line text
        const lines = text.split('\n');
        lines.forEach((lineText, index) => {
            if (index > 0) {
                terminal.output.appendChild(document.createElement('br'));
            }
            const span = document.createElement('span');
            span.textContent = lineText;
            line.appendChild(span);
        });

        // Remove ALL prompt lines first (prevent duplicates)
        const promptLines = terminal.output.querySelectorAll('.output-line.prompt');
        promptLines.forEach(p => p.remove());

        terminal.output.appendChild(line);

        // Add new prompt line for the active terminal
        if (terminal === this.activeTerminal) {
            const newPrompt = document.createElement('div');
            newPrompt.className = 'output-line prompt';
            newPrompt.textContent = '> _';
            terminal.output.appendChild(newPrompt);
        }

        // Scroll to bottom
        terminal.output.scrollTop = terminal.output.scrollHeight;
    }

    clearTerminal(terminal) {
        if (terminal.output) {
            terminal.output.innerHTML = '';

            if (terminal === this.activeTerminal) {
                const prompt = document.createElement('div');
                prompt.className = 'output-line prompt';
                prompt.textContent = '> _';
                terminal.output.appendChild(prompt);
            }
        }
    }

    // ==========================================
    // TERMINAL STATUS
    // ==========================================
    updateTerminalStatus(terminal, status) {
        const statusDot = terminal.element.querySelector('.status-dot');
        const statusText = terminal.element.querySelector('.status-text');

        if (statusDot) {
            statusDot.className = 'status-dot ' + status;
        }

        if (statusText) {
            const statusMessages = {
                online: 'CONNECTED',
                offline: 'DISCONNECTED',
                idle: 'DEMO MODE',
                connecting: 'CONNECTING...'
            };
            statusText.textContent = statusMessages[status] || status.toUpperCase();
        }
    }

    // ==========================================
    // FOCUS MANAGEMENT
    // ==========================================
    focusTerminal(id) {
        // Remove focus from all terminals
        this.terminals.forEach((term, termId) => {
            term.element.classList.remove('focused');
        });

        // Add focus to selected terminal
        const terminal = this.terminals.get(id);
        if (terminal) {
            terminal.element.classList.add('focused');
            this.activeTerminal = terminal;
        }
    }

    // ==========================================
    // NAVIGATION
    // ==========================================
    initNavigation() {
        const navButtons = document.querySelectorAll('.nav-btn');
        const hubContainer = document.querySelector('.hub-container');
        const sidebarSections = document.querySelectorAll('.sidebar-section');

        navButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const section = btn.dataset.section;

                // Update active state
                navButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // THEME SWITCHING - each section has its own soul
                if (hubContainer) {
                    // Add transition overlay effect
                    hubContainer.classList.add('theme-transitioning');
                    hubContainer.classList.add('layout-transitioning');

                    // Change theme
                    hubContainer.setAttribute('data-theme', section);

                    // Remove transition class after animation
                    setTimeout(() => {
                        hubContainer.classList.remove('theme-transitioning');
                        hubContainer.classList.remove('layout-transitioning');
                    }, 600);
                }

                // LAYOUT SWITCHING - swap sidebar content
                sidebarSections.forEach(sec => {
                    if (sec.dataset.section === section) {
                        sec.classList.add('active');
                    } else {
                        sec.classList.remove('active');
                    }
                });

                // ROOM SWITCHING - promote the active room's terminal
                const allTerminals = document.querySelectorAll('.terminal-panel[data-room], .quarters-deck[data-room]');
                allTerminals.forEach(term => {
                    if (term.dataset.room === section) {
                        term.classList.add('active-room');
                    } else {
                        term.classList.remove('active-room');
                    }
                });

                // Focus corresponding terminal
                if (this.terminals.has(section)) {
                    this.focusTerminal(section);
                    const terminal = this.terminals.get(section);
                    if (terminal.input) {
                        terminal.input.focus();
                    }
                }

                // Update cabin states when entering quarters
                if (section === 'captains' && this.updateCabinStates) {
                    this.updateCabinStates();
                }

                // Update crew locations to show who's in the room
                if (window.claudeHub && window.claudeHub.updateCrewLocations) {
                    window.claudeHub.updateCrewLocations();
                }

                // Walkies persist across room changes - no reset needed

                // Clear old invite system (legacy)
                if (this.invitedCrew) {
                    this.invitedCrew.clear();
                    document.querySelectorAll('.crew-dot').forEach(dot => {
                        dot.classList.remove('invited');
                        dot.classList.remove('en-route');
                    });
                }

                // Play sound
                if (window.soundSystem) {
                    window.soundSystem.playChirp();
                }
            });
        });
    }

    // ==========================================
    // SESSION MANAGEMENT
    // ==========================================
    initSessions() {
        const sessionItems = document.querySelectorAll('.session-item');
        const newSessionBtn = document.querySelector('.new-session-btn');

        sessionItems.forEach(item => {
            item.addEventListener('click', () => {
                sessionItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');

                const sessionName = item.querySelector('.session-name').textContent;

                // TODO: Load session from backend
                if (this.activeTerminal) {
                    this.appendOutput(this.activeTerminal, `Switching to session: ${sessionName}`, 'system');
                }

                if (window.soundSystem) {
                    window.soundSystem.playChirp();
                }
            });
        });

        if (newSessionBtn) {
            newSessionBtn.addEventListener('click', () => {
                // TODO: Create new session via backend
                if (window.ambientSystem) {
                    window.ambientSystem.showToast('New session created');
                }

                if (window.soundSystem) {
                    window.soundSystem.playConfirm();
                }
            });
        }
    }

    // ==========================================
    // KEYBOARD SHORTCUTS
    // ==========================================
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+1-4 to switch terminals
            if (e.ctrlKey && e.key >= '1' && e.key <= '4') {
                e.preventDefault();
                const terminals = ['claude', 'server', 'personal', 'science', 'games', 'nav', 'med', 'observatory'];
                const index = parseInt(e.key) - 1;
                if (terminals[index]) {
                    this.focusTerminal(terminals[index]);
                }
            }

            // Ctrl+L to clear
            if (e.ctrlKey && e.key === 'l') {
                e.preventDefault();
                if (this.activeTerminal) {
                    this.clearTerminal(this.activeTerminal);
                }
            }

            // Escape to blur
            if (e.key === 'Escape') {
                document.activeElement.blur();
            }
        });
    }

    // ==========================================
    // CREW INVITE SYSTEM
    // ==========================================
    initCrewInvites() {
        this.invitedCrew = new Set();
        this.activeEvent = null;
        this.sceneNarrated = false;
        this.maxInvites = 3;

        // Click handlers for all crew dots (existing)
        document.querySelectorAll('.crew-dot').forEach(dot => {
            dot.addEventListener('click', (e) => {
                const crewId = dot.dataset.crew;
                this.toggleCrewInvite(crewId, dot);
            });
        });

        // Click handlers for crew roster items (Bridge sidebar)
        document.querySelectorAll('.crew-loc-item').forEach(item => {
            const crewId = item.dataset.crew;

            // Click anywhere on the row to invite
            item.addEventListener('click', (e) => {
                // Don't trigger if clicking the indicator (that's for dismiss)
                if (e.target.classList.contains('loc-indicator')) return;

                // Toggle the walkie for this crew member
                this.toggleWalkie(crewId);
            });

            // Click indicator to dismiss walkie
            const indicator = item.querySelector('.loc-indicator');
            if (indicator) {
                indicator.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (this.openWalkies.has(crewId)) {
                        this.toggleWalkie(crewId);
                    }
                });
            }
        });
    }

    updateRosterUI() {
        document.querySelectorAll('.crew-loc-item').forEach(item => {
            const crewId = item.dataset.crew;
            const isOpen = this.openWalkies.has(crewId);
            item.classList.toggle('walkie-active', isOpen);

            const indicator = item.querySelector('.loc-indicator');
            if (indicator) {
                indicator.classList.toggle('on-comms', isOpen);
            }
        });
    }

    initWalkieSlots() {
        // Initialize the 3 walkie slots
        this.walkieSlots = [
            { slot: 1, crewId: null, ws: null },
            { slot: 2, crewId: null, ws: null },
            { slot: 3, crewId: null, ws: null }
        ];

        // Set up close button handlers
        document.querySelectorAll('.walkie-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const slot = e.target.closest('.walkie-slot');
                const slotNum = parseInt(slot.dataset.slot);
                this.closeWalkieSlot(slotNum);
            });
        });

        // Set up input handlers for walkie slots
        document.querySelectorAll('.walkie-input').forEach(input => {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    const slot = e.target.closest('.walkie-slot');
                    const slotNum = parseInt(slot.dataset.slot);
                    this.sendWalkieMessage(slotNum, input.value);
                    input.value = '';
                }
            });

            // Focus/blur to expand/collapse walkie
            input.addEventListener('focus', () => {
                const slot = input.closest('.walkie-slot');
                document.querySelectorAll('.walkie-slot').forEach(s => s.classList.remove('focused'));
                slot.classList.add('focused');
            });
        });

        // Click anywhere on walkie to focus it
        document.querySelectorAll('.walkie-slot').forEach(slot => {
            slot.addEventListener('click', (e) => {
                if (!e.target.classList.contains('walkie-close')) {
                    document.querySelectorAll('.walkie-slot').forEach(s => s.classList.remove('focused'));
                    slot.classList.add('focused');
                    slot.querySelector('.walkie-input')?.focus();
                }
            });
        });

        // Click outside walkies to unfocus
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.walkie-slot')) {
                document.querySelectorAll('.walkie-slot').forEach(s => s.classList.remove('focused'));
            }
        });
    }

    toggleWalkie(crewId, options = {}) {
        const crewName = this.crewNames[crewId] || crewId;

        // Check if already in a slot
        const existingSlot = this.walkieSlots.find(s => s.crewId === crewId);
        if (existingSlot) {
            // Close this walkie
            this.closeWalkieSlot(existingSlot.slot);
            return;
        }

        // Find empty slot
        const emptySlot = this.walkieSlots.find(s => s.crewId === null);
        if (!emptySlot) {
            if (window.ambientSystem) {
                window.ambientSystem.showToast('All walkie channels in use');
            }
            return;
        }

        // Open walkie in this slot
        this.openWalkieSlot(emptySlot.slot, crewId, options);
    }

    openWalkieSlot(slotNum, crewId, options = {}) {
        const slot = this.walkieSlots.find(s => s.slot === slotNum);
        if (!slot) return;

        const crewName = this.crewNames[crewId] || crewId;
        const slotEl = document.getElementById(`walkie-slot-${slotNum}`);

        // Update slot data
        slot.crewId = crewId;
        slot.cabinVisit = options.cabinVisit || false;  // Track if this is a cabin visit

        // Update UI
        slotEl.classList.add('active');
        if (slot.cabinVisit) {
            slotEl.classList.add('cabin-visit');
        }
        slotEl.querySelector('.walkie-name').textContent = crewName.toUpperCase();
        slotEl.querySelector('.walkie-input').disabled = false;
        slotEl.querySelector('.walkie-input').placeholder = slot.cabinVisit
            ? `${crewName}'s cabin...`
            : `message ${crewName}...`;

        // Clear previous output
        const output = slotEl.querySelector('.walkie-output');
        output.innerHTML = '';

        // Connect WebSocket to crew's terminal
        this.connectWalkieSocket(slotNum, crewId, slot.cabinVisit);

        // Track in openWalkies set for roster UI
        this.openWalkies.add(crewId);
        this.updateRosterUI();

        if (this.activeTerminal) {
            this.appendOutput(this.activeTerminal, `*opened channel to ${crewName}*`, 'system walkie-event');
        }

        if (window.soundSystem) {
            window.soundSystem.playChirp();
        }

        console.log(`[Walkie] Slot ${slotNum} → ${crewName}`);
    }

    closeWalkieSlot(slotNum) {
        const slot = this.walkieSlots.find(s => s.slot === slotNum);
        if (!slot || !slot.crewId) return;

        const crewName = this.crewNames[slot.crewId] || slot.crewId;
        const slotEl = document.getElementById(`walkie-slot-${slotNum}`);

        // Close WebSocket
        if (slot.ws) {
            slot.ws.close();
            slot.ws = null;
        }

        // Update tracking
        this.openWalkies.delete(slot.crewId);

        // Clear slot data
        slot.crewId = null;
        slot.cabinVisit = false;

        // Update UI
        slotEl.classList.remove('active');
        slotEl.classList.remove('cabin-visit');
        slotEl.querySelector('.walkie-name').textContent = '—';
        slotEl.querySelector('.walkie-input').disabled = true;
        slotEl.querySelector('.walkie-input').placeholder = '...';
        slotEl.querySelector('.walkie-output').innerHTML = '';

        this.updateRosterUI();

        if (this.activeTerminal) {
            this.appendOutput(this.activeTerminal, `*closed channel to ${crewName}*`, 'system walkie-event');
        }

        console.log(`[Walkie] Slot ${slotNum} closed`);
    }

    connectWalkieSocket(slotNum, crewId, cabinVisit = false) {
        const slot = this.walkieSlots.find(s => s.slot === slotNum);
        if (!slot) return;

        const slotEl = document.getElementById(`walkie-slot-${slotNum}`);
        const output = slotEl.querySelector('.walkie-output');

        // Add cabin_visit query param if applicable
        const wsUrl = cabinVisit
            ? `${this.wsUrl}/terminal/${crewId}?cabin_visit=true`
            : `${this.wsUrl}/terminal/${crewId}`;

        try {
            slot.ws = new WebSocket(wsUrl);

            slot.ws.onopen = () => {
                console.log(`[Walkie] Slot ${slotNum} connected to ${crewId}`);
                this.appendWalkieOutput(slotNum, '*channel open*', 'system');
            };

            slot.ws.onmessage = (event) => {
                this.handleWalkieMessage(slotNum, event.data);
            };

            slot.ws.onclose = () => {
                console.log(`[Walkie] Slot ${slotNum} disconnected`);
            };

            slot.ws.onerror = () => {
                this.appendWalkieOutput(slotNum, '*connection failed*', 'error');
            };

        } catch (error) {
            console.error(`[Walkie] Connection error:`, error);
        }
    }

    handleWalkieMessage(slotNum, data) {
        try {
            const message = JSON.parse(data);
            const slotEl = document.getElementById(`walkie-slot-${slotNum}`);

            switch (message.type) {
                case 'stream_start':
                    // Start streaming response
                    const streamLine = document.createElement('div');
                    streamLine.className = 'walkie-stream';
                    slotEl.querySelector('.walkie-output').appendChild(streamLine);
                    break;

                case 'stream':
                    const stream = slotEl.querySelector('.walkie-stream:last-child');
                    if (stream) {
                        stream.textContent += message.data;
                    }
                    break;

                case 'stream_end':
                    const ended = slotEl.querySelector('.walkie-stream:last-child');
                    if (ended) {
                        ended.classList.remove('walkie-stream');
                    }
                    // Scroll to bottom
                    const output = slotEl.querySelector('.walkie-output');
                    output.scrollTop = output.scrollHeight;
                    break;

                case 'output':
                    this.appendWalkieOutput(slotNum, message.data);
                    break;
            }
        } catch {
            // Plain text
            this.appendWalkieOutput(slotNum, data);
        }
    }

    appendWalkieOutput(slotNum, text, className = '') {
        const slotEl = document.getElementById(`walkie-slot-${slotNum}`);
        const output = slotEl.querySelector('.walkie-output');

        const line = document.createElement('div');
        line.className = `walkie-line ${className}`;
        line.textContent = text;
        output.appendChild(line);
        output.scrollTop = output.scrollHeight;
    }

    sendWalkieMessage(slotNum, message) {
        if (!message.trim()) return;

        const slot = this.walkieSlots.find(s => s.slot === slotNum);
        if (!slot || !slot.ws || slot.ws.readyState !== WebSocket.OPEN) {
            this.appendWalkieOutput(slotNum, '*channel not connected*', 'error');
            return;
        }

        // Show sent message
        this.appendWalkieOutput(slotNum, `> ${message}`, 'sent');

        // Send to server with walkie flag (bypasses location check - reach person wherever they are)
        slot.ws.send(JSON.stringify({
            type: 'input',
            data: message,
            cabin_visit: slot.cabinVisit || false,
            walkie: true
        }));
    }

    async toggleCrewInvite(crewId, dot) {
        const crewName = this.crewNames[crewId] || crewId;

        if (this.invitedCrew.has(crewId)) {
            // Remove from invited (they leave)
            this.invitedCrew.delete(crewId);
            document.querySelectorAll(`.crew-dot[data-crew="${crewId}"]`).forEach(d => {
                d.classList.remove('invited');
                d.classList.remove('en-route');
            });

            if (this.activeTerminal) {
                this.appendOutput(this.activeTerminal, `*${crewName} has left*`, 'system crew-event');
            }

            if (this.invitedCrew.size === 0 && this.activeEvent) {
                this.endCrewEvent();
                this.sceneNarrated = false;
            }
        } else if (this.pendingArrivals.has(crewId)) {
            // Already en route - cancel?
            if (this.activeTerminal) {
                this.appendOutput(this.activeTerminal, `*${crewName} is already on their way*`, 'system crew-event');
            }
        } else {
            // Schedule arrival via API
            const destination = this.activeTerminal?.id || 'claude';

            try {
                const response = await fetch(`${this.apiUrl}/crew/invite/${crewId}?destination=${destination}`, {
                    method: 'POST'
                });

                if (response.ok) {
                    const data = await response.json();

                    if (data.status === 'invited') {
                        // Mark as en route
                        this.pendingArrivals.set(crewId, data.arrival);
                        document.querySelectorAll(`.crew-dot[data-crew="${crewId}"]`).forEach(d => {
                            d.classList.add('en-route');
                        });

                        if (this.activeTerminal) {
                            this.appendOutput(this.activeTerminal, `*${crewName} is on their way...*`, 'system crew-event en-route');
                        }

                        // Start event if first invite
                        if (!this.activeEvent) {
                            this.startCrewEvent();
                        }
                    } else if (data.status === 'already_invited') {
                        if (this.activeTerminal) {
                            this.appendOutput(this.activeTerminal, `*${crewName} is already coming*`, 'system crew-event');
                        }
                    }
                }
            } catch (error) {
                console.error('[Crew] Invite failed:', error);
                // Fallback to instant invite for offline mode
                this.invitedCrew.add(crewId);
                document.querySelectorAll(`.crew-dot[data-crew="${crewId}"]`).forEach(d => {
                    d.classList.add('invited');
                });
                if (this.activeTerminal) {
                    this.appendOutput(this.activeTerminal, `*${crewName} on comms*`, 'system crew-event');
                }
            }
        }

        console.log('[Crew] Invited:', Array.from(this.invitedCrew), 'En route:', Array.from(this.pendingArrivals.keys()));

        if (window.soundSystem) {
            window.soundSystem.playChirp();
        }
    }

    handleArrivalUpdate(data) {
        // Called when server sends arrival_update via WebSocket
        const { crew_id, destination, status, delay_reason } = data;
        const crewName = this.crewNames[crew_id] || crew_id;

        // Only care about arrivals to our current room
        if (destination !== this.activeTerminal?.id) {
            return;
        }

        if (status === 'arrived') {
            // They made it!
            this.pendingArrivals.delete(crew_id);
            this.invitedCrew.add(crew_id);

            document.querySelectorAll(`.crew-dot[data-crew="${crew_id}"]`).forEach(d => {
                d.classList.remove('en-route');
                d.classList.add('invited');
            });

            if (this.activeEvent) {
                this.activeEvent.participants.add(crew_id);
            }

            if (this.activeTerminal) {
                this.appendOutput(this.activeTerminal, `*${crewName} arrives*`, 'system crew-event arrival');
            }

            if (window.soundSystem) {
                window.soundSystem.playChirp();
            }

        } else if (status === 'delayed') {
            // Running late
            if (this.activeTerminal) {
                this.appendOutput(this.activeTerminal, `*${crewName} is running late... ${delay_reason}*`, 'system crew-event delayed');
            }

        } else if (status === 'no_show') {
            // Not coming
            this.pendingArrivals.delete(crew_id);

            document.querySelectorAll(`.crew-dot[data-crew="${crew_id}"]`).forEach(d => {
                d.classList.remove('en-route');
            });

            if (this.activeTerminal) {
                this.appendOutput(this.activeTerminal, `*${crewName} isn't coming... ${delay_reason}*`, 'system crew-event no-show');
            }
        }

        this.updateRosterUI();
    }

    startCrewEvent() {
        this.activeEvent = {
            startTime: Date.now(),
            room: this.activeTerminal?.id,
            participants: new Set([this.activeTerminal?.id]),
            messages: []
        };
        console.log('[Crew Event] Started in', this.activeEvent.room);
    }

    async endCrewEvent() {
        if (!this.activeEvent) return;

        this.activeEvent.endTime = Date.now();
        const duration = this.activeEvent.endTime - this.activeEvent.startTime;
        console.log('[Crew Event] Ended:', this.activeEvent);

        // Only compress if there were actual messages and it lasted more than a few seconds
        if (this.activeEvent.messages.length > 0 && duration > 5000) {
            console.log('[Memory] Compressing shared event...');

            try {
                const response = await fetch(`${CONFIG.API_URL}/memory/compress`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        participants: Array.from(this.activeEvent.participants),
                        room: this.activeEvent.room,
                        messages: this.activeEvent.messages,
                        duration_ms: duration
                    })
                });

                const memory = await response.json();
                console.log('[Memory] Compressed:', memory);

                if (memory.residue) {
                    // Store in localStorage for each participant
                    this.activeEvent.participants.forEach(participantId => {
                        const key = `claude-hub-${participantId}-shared-memories`;
                        const existing = JSON.parse(localStorage.getItem(key) || '[]');
                        existing.push(memory);
                        // Keep last 10 shared memories per crew member
                        if (existing.length > 10) existing.shift();
                        localStorage.setItem(key, JSON.stringify(existing));
                    });

                    // Show subtle indicator that moment was captured
                    if (this.activeTerminal) {
                        this.appendOutput(this.activeTerminal, `*moment preserved*`, 'system memory-captured');
                    }
                }
            } catch (error) {
                console.error('[Memory] Compression failed:', error);
            }
        }

        this.activeEvent = null;
    }

    getInvitedCrew() {
        return Array.from(this.invitedCrew);
    }

    async getCrewToRespond(roomId) {
        // Combine: crew physically in the room + manually invited crew
        const crewSet = new Set(this.invitedCrew || []);

        try {
            // Fetch crew currently in this room from server
            const response = await fetch(`${this.apiUrl}/room/${roomId}/who`);
            if (response.ok) {
                const data = await response.json();
                // Add each crew member present (except the room owner)
                for (const crew of data.present || []) {
                    if (crew.crew_id !== roomId) {
                        crewSet.add(crew.crew_id);
                    }
                }
            }
        } catch (e) {
            console.log('[Room] Could not fetch room occupants:', e);
        }

        return Array.from(crewSet);
    }

    async pollCrewMembers(hostTerminal, userMessage, crewList) {
        const crewNames = {
            claude: 'Bridge',
            server: 'Engineering',
            personal: 'Ready Room',
            games: 'Holodeck',
            science: 'Science',
            med: 'Medbay',
            nav: 'Navigation'
        };

        // Get recent context from current terminal
        const recentContext = hostTerminal.conversationHistory?.slice(-6) || [];

        // SCENE NARRATION - on first message after crew arrives
        if (!this.sceneNarrated && crewList.length > 0) {
            this.sceneNarrated = true;
            try {
                // Get visitor vibe from their recent context
                let visitorVibe = '';
                if (crewList.length > 0) {
                    const visitorTerminal = this.terminals.get(crewList[0]);
                    const lastMsg = visitorTerminal?.conversationHistory?.slice(-1)[0];
                    if (lastMsg?.content) {
                        visitorVibe = lastMsg.content.substring(0, 100);
                    }
                }

                const sceneResponse = await fetch(`${CONFIG.API_URL}/scene/narrate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        room: hostTerminal.id,
                        visitors: crewList,
                        host_vibe: recentContext.slice(-1)[0]?.content?.substring(0, 100) || '',
                        visitor_vibe: visitorVibe
                    })
                });
                const scene = await sceneResponse.json();
                if (scene.narration) {
                    this.appendOutput(hostTerminal, scene.narration, 'system scene-narration');
                }
            } catch (e) {
                console.log('[Scene] Narration skipped:', e);
            }
        }

        // Poll each crew member in parallel (room occupants + invited)
        console.log(`[Crew Poll] Polling ${crewList.length} crew members...`);
        console.log(`[Crew Poll] Host terminal:`, hostTerminal?.id);
        console.log(`[Crew Poll] User message:`, userMessage);
        console.log(`[Crew Poll] Context:`, recentContext);

        const polls = crewList.map(async (crewId) => {
            console.log(`[Crew Poll] Sending poll to ${crewId}...`);

            // Get the invited crew member's OWN recent context (from their home terminal)
            const crewTerminal = this.terminals.get(crewId);
            const crewOwnContext = crewTerminal?.conversationHistory?.slice(-6) || [];

            const payload = {
                crew_id: crewId,
                host_room: hostTerminal.id,
                user_message: userMessage,
                context: recentContext,
                crew_own_context: crewOwnContext  // Their recent convo before coming here
            };
            console.log(`[Crew Poll] Payload:`, JSON.stringify(payload));
            try {
                const response = await fetch(`${CONFIG.API_URL}/crew/poll`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                console.log(`[Crew Poll] Fetch completed for ${crewId}`);

                console.log(`[Crew Poll] Got response from ${crewId}:`, response.status);
                const data = await response.json();
                console.log(`[Crew Poll] Data from ${crewId}:`, data);
                return { crewId, ...data };
            } catch (error) {
                console.error(`[Crew Poll] Error polling ${crewId}:`, error);
                return { crewId, action: 'silence' };
            }
        });

        // Wait for all polls
        const results = await Promise.all(polls);

        // Display results in terminal
        for (const result of results) {
            const name = crewNames[result.crewId];
            const speakerClass = `speaker-${result.crewId}`;

            console.log(`[Crew Poll] ${name} responded:`, result);

            if (result.action === 'silence') {
                // They chose not to respond - optionally show nothing or subtle indicator
                console.log(`[Crew Poll] ${name} chose silence`);
            } else if (result.emote && result.speech) {
                this.appendOutput(hostTerminal, `${name}: *${result.emote}*`, `crew-response emote ${speakerClass}`);
                this.appendOutput(hostTerminal, `${name}: "${result.speech}"`, `crew-response speech ${speakerClass}`);
            } else if (result.emote) {
                this.appendOutput(hostTerminal, `${name}: *${result.emote}*`, `crew-response emote ${speakerClass}`);
            } else if (result.speech) {
                this.appendOutput(hostTerminal, `${name}: "${result.speech}"`, `crew-response speech ${speakerClass}`);
            }

            // Track in event
            if (this.activeEvent && result.action !== 'silence') {
                this.activeEvent.messages.push({
                    from: result.crewId,
                    type: result.action,
                    emote: result.emote,
                    speech: result.speech,
                    timestamp: Date.now()
                });
            }
        }

        // Return responses so host terminal knows what visitors said
        return results.filter(r => r.action !== 'silence').map(r => ({
            crew: crewNames[r.crewId],
            crewId: r.crewId,
            emote: r.emote,
            speech: r.speech
        }));
    }

    // ==========================================
    // CREW CABIN SYSTEM
    // ==========================================
    initCrewCabins() {
        this.cabinStates = new Map(); // crew_id -> { isHome, activity }
        this.openCabins = new Set(); // Track which cabin terminals are open

        // Map crew IDs to cabin terminal IDs
        this.crewToCabin = {
            'server': 'cabin-alex',
            'personal': 'cabin-dq',
            'science': 'cabin-mira',
            'med': 'cabin-ryn'
        };

        // Set up click handlers for cabin cards to toggle terminals
        document.querySelectorAll('.cabin-card').forEach(card => {
            card.addEventListener('click', () => {
                const crewId = card.dataset.crew;
                const cabinId = this.crewToCabin[crewId];

                if (!cabinId) return; // Skip if no matching cabin terminal

                this.toggleCabinTerminal(cabinId, card);
            });
        });

        // Poll crew locations periodically for status updates
        this.updateCabinStates();
        setInterval(() => this.updateCabinStates(), 30000); // Every 30 seconds

        // Load note history
        this.loadNoteHistory();

        // Initialize drag/resize for cabin terminals
        this.initCabinDragResize();
    }

    initCabinDragResize() {
        const cabinTerminals = document.querySelectorAll('.cabin-terminal'); // Include all cabins now

        cabinTerminals.forEach(terminal => {
            // Add drag handle to header
            const header = terminal.querySelector('.cabin-header');
            if (!header) return;

            header.style.cursor = 'move';
            header.setAttribute('data-drag-handle', 'true');

            // Add resize handle
            const resizeHandle = document.createElement('div');
            resizeHandle.className = 'cabin-resize-handle';
            resizeHandle.innerHTML = '⋰';
            terminal.appendChild(resizeHandle);

            // Load saved position/size
            const savedState = this.loadCabinState(terminal.id);
            if (savedState && (savedState.x !== undefined || savedState.y !== undefined)) {
                terminal.style.position = 'absolute';
                terminal.style.margin = '0';
                if (savedState.x !== undefined) terminal.style.left = savedState.x + 'px';
                if (savedState.y !== undefined) terminal.style.top = savedState.y + 'px';
                if (savedState.width) terminal.style.width = savedState.width + 'px';
                if (savedState.height) terminal.style.height = savedState.height + 'px';
            }

            // Drag functionality
            let isDragging = false;
            let dragStartX, dragStartY, currentX, currentY;

            header.addEventListener('mousedown', (e) => {
                if (!e.target.closest('[data-drag-handle]')) return;

                // Get current position before switching to absolute
                const rect = terminal.getBoundingClientRect();
                const parentRect = terminal.parentElement.getBoundingClientRect();

                // If not already positioned, set initial position to maintain current location
                if (terminal.style.position !== 'absolute') {
                    currentX = rect.left - parentRect.left;
                    currentY = rect.top - parentRect.top;
                    terminal.style.position = 'absolute';
                    terminal.style.left = currentX + 'px';
                    terminal.style.top = currentY + 'px';
                    terminal.style.margin = '0'; // Remove flex margins
                } else {
                    currentX = parseFloat(terminal.style.left) || 0;
                    currentY = parseFloat(terminal.style.top) || 0;
                }

                isDragging = true;
                dragStartX = e.clientX;
                dragStartY = e.clientY;

                terminal.classList.add('dragging');
                e.preventDefault();
            });

            document.addEventListener('mousemove', (e) => {
                if (!isDragging) return;

                const dx = e.clientX - dragStartX;
                const dy = e.clientY - dragStartY;

                terminal.style.left = (currentX + dx) + 'px';
                terminal.style.top = (currentY + dy) + 'px';
            });

            document.addEventListener('mouseup', () => {
                if (isDragging) {
                    isDragging = false;
                    terminal.classList.remove('dragging');

                    // Update current position for next drag
                    currentX = parseFloat(terminal.style.left) || 0;
                    currentY = parseFloat(terminal.style.top) || 0;

                    this.saveCabinState(terminal.id);
                }
            });

            // Resize functionality
            let isResizing = false;
            let resizeStartX, resizeStartY, resizeStartWidth, resizeStartHeight;

            resizeHandle.addEventListener('mousedown', (e) => {
                isResizing = true;
                resizeStartX = e.clientX;
                resizeStartY = e.clientY;
                resizeStartWidth = terminal.offsetWidth;
                resizeStartHeight = terminal.offsetHeight;

                terminal.classList.add('resizing');
                e.preventDefault();
                e.stopPropagation();
            });

            document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;

                const dx = e.clientX - resizeStartX;
                const dy = e.clientY - resizeStartY;

                const newWidth = Math.max(250, resizeStartWidth + dx);
                const newHeight = Math.max(150, resizeStartHeight + dy);

                terminal.style.width = newWidth + 'px';
                terminal.style.height = newHeight + 'px';
            });

            document.addEventListener('mouseup', () => {
                if (isResizing) {
                    isResizing = false;
                    terminal.classList.remove('resizing');
                    this.saveCabinState(terminal.id);
                }
            });
        });
    }

    saveCabinState(cabinId) {
        const terminal = document.getElementById(cabinId);
        if (!terminal) return;

        const state = {
            x: parseInt(terminal.style.left) || undefined,
            y: parseInt(terminal.style.top) || undefined,
            width: parseInt(terminal.style.width) || undefined,
            height: parseInt(terminal.style.height) || undefined
        };

        localStorage.setItem(`cabin-state-${cabinId}`, JSON.stringify(state));
    }

    loadCabinState(cabinId) {
        const saved = localStorage.getItem(`cabin-state-${cabinId}`);
        return saved ? JSON.parse(saved) : null;
    }

    toggleCabinTerminal(cabinId, card) {
        const terminal = document.getElementById(cabinId);
        if (!terminal) return;

        if (this.openCabins.has(cabinId)) {
            // Close it
            terminal.classList.remove('cabin-open');
            this.openCabins.delete(cabinId);
            card.classList.remove('terminal-open');
        } else {
            // Open it
            terminal.classList.add('cabin-open');
            this.openCabins.add(cabinId);
            card.classList.add('terminal-open');

            // Focus the terminal input
            const input = terminal.querySelector('.cabin-input');
            if (input) {
                setTimeout(() => input.focus(), 100);
            }
        }
    }

    async loadNoteHistory() {
        try {
            const response = await fetch(`${this.apiUrl}/cabin/notes/all`);
            if (!response.ok) return;

            const data = await response.json();
            const notes = data.notes || [];

            const notesContainer = document.getElementById('notes-history');
            const notesCount = document.getElementById('notes-count');

            if (!notesContainer) return;

            if (notes.length === 0) {
                notesContainer.innerHTML = '<div class="notes-empty">No notes yet.</div>';
                if (notesCount) notesCount.textContent = '0';
                return;
            }

            // Update count
            if (notesCount) notesCount.textContent = notes.length.toString();

            // Render notes (show last 5)
            const recentNotes = notes.slice(0, 5);
            notesContainer.innerHTML = recentNotes.map(note => {
                const readClass = note.read ? 'read' : '';
                const timeAgo = this.formatTimeAgo(note.timestamp);
                const truncatedText = note.text.length > 40 ? note.text.slice(0, 40) + '...' : note.text;

                return `
                    <div class="note-item ${readClass}" data-crew="${note.for_crew_id}">
                        <span class="note-recipient">To ${note.for_crew}</span>
                        <span class="note-text">"${truncatedText}"</span>
                        <span class="note-time">${timeAgo}${note.read ? ' - read' : ''}</span>
                    </div>
                `;
            }).join('');

        } catch (error) {
            console.log('[Notes] Could not load note history:', error.message);
        }
    }

    formatTimeAgo(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }

    async updateCabinStates() {
        try {
            const response = await fetch(`${this.apiUrl}/crew/locations`);
            if (!response.ok) return;

            const data = await response.json();
            const locations = data.locations || {};

            // Update each cabin card based on crew location
            document.querySelectorAll('.cabin-card').forEach(card => {
                const crewId = card.dataset.crew;
                const cabinName = card.dataset.cabin;
                const crewLocation = locations[crewId];

                // Check if crew is in their cabin (quarters)
                const isHome = crewLocation?.location === 'quarters' ||
                               crewLocation?.location === cabinName ||
                               crewLocation?.location?.includes('cabin');

                // Update card state
                card.classList.toggle('home', isHome);
                card.classList.toggle('away', !isHome);

                // Update status text
                const statusEl = card.querySelector('.cabin-status');
                if (statusEl) {
                    if (isHome) {
                        statusEl.textContent = crewLocation?.activity || 'in quarters';
                    } else {
                        // Show where they are instead - use location_name from API
                        const loc = crewLocation?.location_name || crewLocation?.location || 'unknown';
                        statusEl.textContent = loc;
                    }
                }

                // Store state
                this.cabinStates.set(crewId, {
                    isHome,
                    location: crewLocation?.location,
                    activity: crewLocation?.activity
                });
            });

        } catch (error) {
            console.log('[Cabins] Could not fetch crew locations:', error.message);
        }
    }

    openCabin(crewId) {
        const crewName = this.crewNames[crewId] || crewId;
        const state = this.cabinStates.get(crewId);
        const isHome = state?.isHome || false;

        // Update active cabin
        document.querySelectorAll('.cabin-card').forEach(card => {
            card.classList.toggle('active', card.dataset.crew === crewId);
        });
        this.activeCabin = crewId;
        this.activeCabinEmpty = !isHome;

        // Get the captains terminal for output
        const captainsTerminal = this.terminals.get('captains');
        if (!captainsTerminal) return;

        if (isHome) {
            // They're home - this is "a moment"
            this.appendOutput(captainsTerminal, `*You knock on ${crewName}'s door...*`, 'system cabin-event');

            // Open a walkie channel to them for the intimate conversation
            this.toggleWalkie(crewId, { cabinVisit: true });

        } else {
            // Empty cabin - can explore, leave notes
            this.appendOutput(captainsTerminal, `*${crewName}'s cabin is empty. The door slides open for you.*`, 'system cabin-event');

            // Fetch and display cabin description
            this.showCabinDescription(crewId, captainsTerminal);

            // Update input placeholder to hint at interaction options
            if (captainsTerminal.input) {
                captainsTerminal.input.placeholder = `think aloud... or /note to leave a message`;
            }
        }
    }

    exitCabin() {
        // Clear cabin state and restore normal terminal behavior
        const captainsTerminal = this.terminals.get('captains');

        document.querySelectorAll('.cabin-card').forEach(card => {
            card.classList.remove('active');
        });

        this.activeCabin = null;
        this.activeCabinEmpty = false;

        if (captainsTerminal?.input) {
            captainsTerminal.input.placeholder = 'private thoughts...';
        }

        if (captainsTerminal) {
            this.appendOutput(captainsTerminal, `*You step back into your own quarters.*`, 'system cabin-event');
        }
    }

    async leaveCabinNote(crewId, noteText) {
        const crewName = this.crewNames[crewId] || crewId;
        const captainsTerminal = this.terminals.get('captains');

        try {
            const response = await fetch(`${this.apiUrl}/cabin/${crewId}/note`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    note: noteText,
                    from_person: 'casey'
                })
            });

            if (response.ok) {
                this.appendOutput(captainsTerminal, `*You leave a note on ${crewName}'s pillow.*`, 'system cabin-event note-left');
                this.appendOutput(captainsTerminal, `"${noteText}"`, 'cabin-note yours');

                // Refresh note history
                this.loadNoteHistory();

                // Exit the cabin after leaving note
                setTimeout(() => this.exitCabin(), 1500);
            } else {
                this.appendOutput(captainsTerminal, `*The note slips from your fingers...*`, 'system cabin-event error');
            }

        } catch (error) {
            console.error('[Cabin] Failed to leave note:', error);
            this.appendOutput(captainsTerminal, `*Something went wrong.*`, 'system error');
        }
    }

    async leaveCabinReflection(crewId, thought) {
        const crewName = this.crewNames[crewId] || crewId;
        const captainsTerminal = this.terminals.get('captains');

        try {
            const response = await fetch(`${this.apiUrl}/cabin/${crewId}/reflection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    thought: thought
                })
            });

            if (response.ok) {
                // More atmospheric response for reflections
                this.appendOutput(captainsTerminal, `*Your words hang in the air of ${crewName}'s empty cabin. Not a note - just a thought, left behind like warmth.*`, 'system cabin-event reflection-left');

                // Don't auto-exit for reflections - let them linger
                setTimeout(() => {
                    this.appendOutput(captainsTerminal, `*Maybe they'll sense you were here.*`, 'system cabin-event dim');
                }, 1000);

            } else {
                this.appendOutput(captainsTerminal, `*The thought fades...*`, 'system cabin-event error');
            }

        } catch (error) {
            console.error('[Cabin] Failed to leave reflection:', error);
        }
    }

    async showCabinDescription(crewId, terminal) {
        try {
            const response = await fetch(`${this.apiUrl}/ship/room/quarters`);
            if (!response.ok) return;

            const data = await response.json();
            const cabinKey = `${crewId === 'claude' ? 'lumen' : crewId === 'server' ? 'alex' : crewId === 'personal' ? 'dq' : crewId === 'science' ? 'mira' : crewId === 'med' ? 'ryn' : crewId}_cabin`;
            const cabin = data.objects?.[cabinKey];

            if (cabin?.description) {
                this.appendOutput(terminal, cabin.description, 'cabin-description dim');
            }

            // Show interactive prompt
            this.appendOutput(terminal, `*You could leave a note, or just... be here for a moment.*`, 'system cabin-prompt');

        } catch (error) {
            console.log('[Cabin] Could not fetch cabin description:', error.message);
        }
    }

    // ==========================================
    // CHECKPOINT SYSTEM
    // ==========================================

    gatherLocalStorage() {
        // Gather all claude-hub related localStorage items
        const data = {};
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('claude-hub-')) {
                try {
                    data[key] = JSON.parse(localStorage.getItem(key));
                } catch {
                    data[key] = localStorage.getItem(key);
                }
            }
        }
        return data;
    }

    restoreLocalStorage(data) {
        // Restore localStorage items from checkpoint
        if (!data) return;

        // Clear existing claude-hub items first
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('claude-hub-')) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach(key => localStorage.removeItem(key));

        // Restore from checkpoint
        for (const [key, value] of Object.entries(data)) {
            if (typeof value === 'object') {
                localStorage.setItem(key, JSON.stringify(value));
            } else {
                localStorage.setItem(key, value);
            }
        }

        console.log(`[Checkpoint] Restored ${Object.keys(data).length} localStorage items`);
    }

    async saveCheckpoint(name = '') {
        const localStorage = this.gatherLocalStorage();

        try {
            const response = await fetch(`${this.apiUrl}/checkpoint/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, localStorage })
            });

            const result = await response.json();

            if (result.success) {
                console.log(`[Checkpoint] Saved: ${result.checkpoint_id}`);
                if (window.ambientSystem) {
                    window.ambientSystem.showToast(`Checkpoint saved: ${result.metadata.name}`);
                }
            }

            return result;
        } catch (error) {
            console.error('[Checkpoint] Save failed:', error);
            return { success: false, error: error.message };
        }
    }

    async listCheckpoints() {
        try {
            const response = await fetch(`${this.apiUrl}/checkpoint/list`);
            return await response.json();
        } catch (error) {
            console.error('[Checkpoint] List failed:', error);
            return { checkpoints: [], count: 0 };
        }
    }

    async restoreCheckpoint(checkpointId) {
        try {
            const response = await fetch(`${this.apiUrl}/checkpoint/restore`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: checkpointId })
            });

            const result = await response.json();

            if (result.success) {
                // Restore localStorage
                if (result.localStorage) {
                    this.restoreLocalStorage(result.localStorage);
                }

                console.log(`[Checkpoint] Restored: ${checkpointId}`);
                if (window.ambientSystem) {
                    window.ambientSystem.showToast(`Restored checkpoint: ${checkpointId}`);
                }

                // Reload page to pick up restored state
                setTimeout(() => window.location.reload(), 1000);
            }

            return result;
        } catch (error) {
            console.error('[Checkpoint] Restore failed:', error);
            return { success: false, error: error.message };
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.terminalManager = new TerminalManager();
    window.terminalManager.initCrewInvites();
    initCheckpointUI();
});

// Global checkpoint helpers for console access
window.checkpoint = {
    save: (name) => window.terminalManager?.saveCheckpoint(name),
    list: () => window.terminalManager?.listCheckpoints(),
    restore: (id) => window.terminalManager?.restoreCheckpoint(id)
};

// Checkpoint UI initialization
function initCheckpointUI() {
    const saveBtn = document.getElementById('checkpoint-save-btn');
    const nameInput = document.getElementById('checkpoint-name');
    const listEl = document.getElementById('checkpoint-list');

    if (!saveBtn || !listEl) return;

    // Save button handler
    saveBtn.addEventListener('click', async () => {
        const name = nameInput?.value?.trim() || '';
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="btn-icon">◇</span> SAVING...';

        const result = await window.terminalManager?.saveCheckpoint(name);

        saveBtn.disabled = false;
        saveBtn.innerHTML = '<span class="btn-icon">◆</span> SAVE';

        if (result?.success) {
            if (nameInput) nameInput.value = '';
            refreshCheckpointList();
        }
    });

    // Enter key to save
    if (nameInput) {
        nameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveBtn.click();
            }
        });
    }

    // Initial load
    refreshCheckpointList();
}

async function refreshCheckpointList() {
    const listEl = document.getElementById('checkpoint-list');
    if (!listEl) return;

    const result = await window.terminalManager?.listCheckpoints();
    const checkpoints = result?.checkpoints || [];

    if (checkpoints.length === 0) {
        listEl.innerHTML = '<div class="checkpoint-empty">No checkpoints yet</div>';
        return;
    }

    listEl.innerHTML = checkpoints.slice(0, 10).map(cp => {
        const date = cp.created ? new Date(cp.created) : null;
        const dateStr = date ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
        const timeStr = date ? date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : '';

        return `
            <div class="checkpoint-item" data-id="${cp.id}">
                <span class="checkpoint-item-name">${cp.name || cp.id}</span>
                <span class="checkpoint-item-date">${dateStr} ${timeStr}</span>
                <button class="checkpoint-item-restore" data-id="${cp.id}">RESTORE</button>
            </div>
        `;
    }).join('');

    // Add click handlers for restore buttons
    listEl.querySelectorAll('.checkpoint-item-restore').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            if (confirm(`Restore checkpoint "${id}"?\n\nThis will reload the page.`)) {
                await window.terminalManager?.restoreCheckpoint(id);
            }
        });
    });
}

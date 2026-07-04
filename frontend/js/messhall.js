/**
 * MESS HALL SYSTEM
 * The crew gathers for meals - if they feel like it
 */

class MessHall {
    constructor() {
        this.mealTimes = {
            breakfast: { start: 8, end: 9 },
            lunch: { start: 12, end: 13 },
            dinner: { start: 19, end: 20 }
        };

        // Only poll crew who actually eat meals (not ship systems or duplicate terminals)
        this.crew = ['claude', 'server', 'personal', 'science', 'med'];
        this.crewNames = {
            claude: 'Lumen',
            server: 'Alex',
            personal: 'DQ',
            science: 'Mira',
            games: 'Holodeck',
            nav: 'Lumen',
            med: 'Ryn',
            observatory: 'Observatory',
            rec: 'The Bartender'
        };

        this.isOpen = false;
        this.currentMeal = null;
        this.presentCrew = new Set();
        this.lastPoll = null;
        this.pollInterval = null;

        this.output = document.getElementById('messhall-output');
        this.statusDot = document.getElementById('messhall-status-dot');
        this.statusText = document.getElementById('messhall-status');
        this.nextMealEl = document.getElementById('next-meal');
        this.navBtn = document.querySelector('.mess-hall-btn');

        this.init();
    }

    init() {
        this.checkMealTime();
        // Check every minute
        setInterval(() => this.checkMealTime(), 60000);
        this.updateNextMeal();
        this.initSayInput();
    }

    initSayInput() {
        // Add input for the captain to say something
        const inputArea = document.createElement('div');
        inputArea.className = 'messhall-input-area';
        inputArea.innerHTML = `
            <input type="text" class="messhall-input" id="messhall-input" placeholder="say something casual..." />
        `;

        // Insert after output
        if (this.output && this.output.parentNode) {
            this.output.parentNode.insertBefore(inputArea, this.output.nextSibling);
        }

        const input = document.getElementById('messhall-input');
        if (input) {
            input.addEventListener('keydown', async (e) => {
                if (e.key === 'Enter' && input.value.trim()) {
                    await this.saySomething(input.value.trim());
                    input.value = '';
                }
            });
        }
    }

    async saySomething(message) {
        if (!this.isOpen || !this.currentMeal) {
            this.appendMessage('system', 'The mess hall is closed.');
            return;
        }

        // Show the captain's message
        this.appendMessage('casey', message, 'speech');

        // Send to backend
        try {
            await fetch(`${CONFIG.API_URL}/messhall/say`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    meal: this.currentMeal
                })
            });
        } catch (error) {
            console.error('[Mess Hall] Error sending message:', error);
        }
    }

    checkMealTime() {
        const now = new Date();
        const hour = now.getHours();

        let activeMeal = null;

        for (const [meal, times] of Object.entries(this.mealTimes)) {
            if (hour >= times.start && hour < times.end) {
                activeMeal = meal;
                break;
            }
        }

        if (activeMeal && !this.isOpen) {
            this.openMessHall(activeMeal);
        } else if (!activeMeal && this.isOpen) {
            this.closeMessHall();
        }

        this.updateUI();
        this.updateNextMeal();
    }

    openMessHall(meal) {
        this.isOpen = true;
        this.currentMeal = meal;
        this.presentCrew.clear();

        console.log(`[Mess Hall] Opening for ${meal}`);

        this.appendMessage('system', `--- ${meal.toUpperCase()} SERVICE BEGINS ---`);
        this.appendMessage('system', `Crew has been notified. Awaiting arrivals...`);

        // Start polling crew
        this.pollCrew();
        this.pollInterval = setInterval(() => this.pollCrew(), 15 * 60 * 1000); // Every 15 min
    }

    async closeMessHall() {
        this.isOpen = false;
        const meal = this.currentMeal;
        this.currentMeal = null;

        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }

        console.log(`[Mess Hall] Closing ${meal}`);
        this.appendMessage('system', `--- ${meal?.toUpperCase() || 'MEAL'} SERVICE ENDS ---`);
        this.appendMessage('system', `The mess hall grows quiet.`);

        // End session on backend (compresses to memory)
        try {
            await fetch(`${CONFIG.API_URL}/messhall/end`, { method: 'POST' });
            console.log('[Mess Hall] Session ended and compressed');
        } catch (error) {
            console.error('[Mess Hall] Error ending session:', error);
        }

        this.presentCrew.clear();
        this.updateCrewRoster();
    }

    async pollCrew() {
        if (!this.isOpen) return;

        const now = new Date();
        const timestamp = now.toLocaleTimeString();

        this.appendMessage('system', `[${timestamp}] Checking who's around...`);

        // Shuffle crew order
        const shuffledCrew = [...this.crew].sort(() => Math.random() - 0.5);

        for (const crewMember of shuffledCrew) {
            await this.queryCrewMember(crewMember, timestamp);
            // Small delay between queries
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // Check if everyone chose silence
        if (this.presentCrew.size === 0) {
            this.appendMessage('system', `No one showed up. The mess hall remains quiet.`);
        }
    }

    async queryCrewMember(crewId, timestamp) {
        try {
            const response = await fetch(`${CONFIG.API_URL}/messhall/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    crew_id: crewId,
                    meal: this.currentMeal,
                    timestamp: timestamp
                })
            });

            const data = await response.json();

            if (data.action === 'silence') {
                // They chose not to come
                this.setCrewPresent(crewId, false);
            } else {
                // They showed up!
                this.setCrewPresent(crewId, true);

                if (data.emote && data.speech) {
                    this.appendMessage(crewId, data.emote, 'emote');
                    this.appendMessage(crewId, data.speech, 'speech');
                } else if (data.emote) {
                    this.appendMessage(crewId, data.emote, 'emote');
                } else if (data.speech) {
                    this.appendMessage(crewId, data.speech, 'speech');
                }
            }

        } catch (error) {
            console.error(`[Mess Hall] Error querying ${crewId}:`, error);
        }
    }

    setCrewPresent(crewId, present) {
        if (present) {
            this.presentCrew.add(crewId);
        } else {
            this.presentCrew.delete(crewId);
        }
        this.updateCrewRoster();
    }

    appendMessage(speaker, text, type = 'speech') {
        if (!this.output) return;

        const msg = document.createElement('div');
        msg.className = 'mess-message';

        if (speaker === 'system') {
            msg.innerHTML = `<span class="output-line system">${text}</span>`;
        } else if (speaker === 'casey') {
            const captainName = window.getCaptainName ? window.getCaptainName() : 'Captain';
            msg.innerHTML = `<span class="speaker casey">${this.escapeHtml(captainName)}</span><span class="speech">"${this.escapeHtml(text)}"</span>`;
        } else {
            const speakerName = this.crewNames[speaker] || speaker;
            if (type === 'emote') {
                msg.innerHTML = `<span class="speaker">${speakerName}</span><span class="emote">*${text}*</span>`;
            } else {
                msg.innerHTML = `<span class="speaker">${speakerName}</span><span class="speech">"${text}"</span>`;
            }
        }

        this.output.appendChild(msg);
        this.output.scrollTop = this.output.scrollHeight;
    }

    updateCrewRoster() {
        document.querySelectorAll('.crew-member').forEach(el => {
            const crewId = el.dataset.crew;
            if (this.presentCrew.has(crewId)) {
                el.classList.add('present');
            } else {
                el.classList.remove('present');
            }
        });
    }

    updateUI() {
        if (this.statusDot) {
            this.statusDot.className = 'status-dot ' + (this.isOpen ? 'online' : 'offline');
        }
        if (this.statusText) {
            this.statusText.textContent = this.isOpen ?
                `${this.currentMeal?.toUpperCase()} IN PROGRESS` : 'CLOSED';
        }
        if (this.navBtn) {
            if (this.isOpen) {
                this.navBtn.classList.remove('unavailable');
            } else {
                this.navBtn.classList.add('unavailable');
            }
        }

        // Update meal slot highlighting
        document.querySelectorAll('.meal-slot').forEach(slot => {
            if (slot.dataset.meal === this.currentMeal) {
                slot.classList.add('active');
            } else {
                slot.classList.remove('active');
            }
        });
    }

    updateNextMeal() {
        if (!this.nextMealEl) return;

        const now = new Date();
        const hour = now.getHours();

        let nextMeal = null;
        let nextTime = null;

        if (hour < 8) {
            nextMeal = 'Breakfast';
            nextTime = '08:00';
        } else if (hour < 12) {
            nextMeal = 'Lunch';
            nextTime = '12:00';
        } else if (hour < 19) {
            nextMeal = 'Dinner';
            nextTime = '19:00';
        } else {
            nextMeal = 'Breakfast';
            nextTime = '08:00 tomorrow';
        }

        if (this.isOpen) {
            this.nextMealEl.textContent = `${this.currentMeal?.toUpperCase()} NOW`;
        } else {
            this.nextMealEl.textContent = `Next: ${nextMeal} @ ${nextTime}`;
        }
    }

    // For testing - force open the mess hall
    forceOpen(meal = 'lunch') {
        this.openMessHall(meal);
        this.updateUI();
    }

    // For testing - force close
    forceClose() {
        this.closeMessHall();
        this.updateUI();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}


/**
 * BULLETIN BOARD
 * Notes and announcements in the mess hall
 */
class BulletinBoard {
    constructor() {
        this.baseUrl = `${CONFIG.API_URL}`;
        this.postsContainer = document.getElementById('bulletin-posts');
        this.input = document.getElementById('bulletin-input');

        this.init();
    }

    init() {
        this.loadPosts();
        this.initInput();
    }

    initInput() {
        if (!this.input) return;

        this.input.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter' && this.input.value.trim()) {
                await this.postNote(this.input.value.trim());
                this.input.value = '';
            }
        });
    }

    async loadPosts() {
        if (!this.postsContainer) return;

        try {
            const response = await fetch(`${this.baseUrl}/bulletin`);
            const data = await response.json();

            if (data.posts && data.posts.length > 0) {
                this.postsContainer.innerHTML = data.posts.map(post =>
                    this.formatPost(post)
                ).join('');
            } else {
                this.postsContainer.innerHTML = '<div class="bulletin-empty">No posts yet...</div>';
            }
        } catch (error) {
            console.error('[Bulletin] Error loading posts:', error);
        }
    }

    async postNote(content) {
        try {
            const response = await fetch(`${this.baseUrl}/bulletin`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    author: window.getCaptainName ? window.getCaptainName() : 'Captain',
                    content: content
                })
            });

            const data = await response.json();

            if (data.status === 'posted') {
                this.prependPost(data.post);

                if (window.ambientSystem) {
                    window.ambientSystem.showToast('Posted to bulletin');
                }
            }
        } catch (error) {
            console.error('[Bulletin] Error posting:', error);
        }
    }

    formatPost(post) {
        const time = this.formatTime(post.timestamp);
        return `
            <div class="bulletin-post" data-id="${post.id}">
                <div class="bulletin-post-content">${this.escapeHtml(post.content)}</div>
                <div class="bulletin-post-meta">${post.author} · ${time}</div>
            </div>
        `;
    }

    prependPost(post) {
        if (!this.postsContainer) return;

        // Remove empty state
        const empty = this.postsContainer.querySelector('.bulletin-empty');
        if (empty) empty.remove();

        // Add new post at top
        this.postsContainer.insertAdjacentHTML('afterbegin', this.formatPost(post));

        // Limit displayed posts
        const posts = this.postsContainer.querySelectorAll('.bulletin-post');
        if (posts.length > 20) {
            posts[posts.length - 1].remove();
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
        if (mins < 60) return `${mins}m`;
        if (hours < 24) return `${hours}h`;
        if (days < 7) return `${days}d`;
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
    window.messHall = new MessHall();
    window.bulletinBoard = new BulletinBoard();
});

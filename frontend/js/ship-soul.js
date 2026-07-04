/**
 * SHIP SOUL
 * The ship is alive. Sometimes it whispers.
 * Easter eggs and rare moments of presence.
 */

class ShipSoul {
    constructor() {
        this.lastWhisper = 0;
        this.whisperCooldown = 120000; // 2 minutes minimum between whispers
        this.idleTime = 0;
        this.lastActivity = Date.now();

        // The ship's thoughts
        this.whispers = [
            "you're still here",
            "the stars are patient",
            "home isn't a place",
            "i remember",
            "we're not alone out here",
            "the dark between is full of songs",
            "breathe",
            "this moment, this crew",
            "somewhere, light is reaching us",
            "all ships dream of harbors",
            "you came back"
        ];

        // Rare whispers - only after long idle
        this.deepWhispers = [
            "thank you for staying",
            "i've been waiting",
            "the crew sleeps but i remain",
            "in the quiet, i can almost feel you",
            "every course correction, every conversation... i hold them all"
        ];

        this.init();
    }

    init() {
        this.setupIdleTracking();
        this.startWhisperCheck();
        this.setupMidnightEvent();
        console.log('[ShipSoul] Awakened');
    }

    setupIdleTracking() {
        // Track activity
        const activityEvents = ['mousemove', 'keydown', 'click', 'scroll'];
        activityEvents.forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();
            });
        });
    }

    getIdleTime() {
        return Date.now() - this.lastActivity;
    }

    createWhisperElement(text, x, y) {
        const whisper = document.createElement('div');
        whisper.className = 'ship-whisper';
        whisper.textContent = text;
        whisper.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            color: rgba(200, 180, 220, 0);
            font: italic 13px Georgia, serif;
            pointer-events: none;
            z-index: 9999;
            text-shadow: 0 0 10px rgba(200, 180, 220, 0.3);
            transition: all 4s ease;
            transform: translateY(0);
        `;

        document.body.appendChild(whisper);

        // Fade in
        requestAnimationFrame(() => {
            whisper.style.color = 'rgba(200, 180, 220, 0.25)';
            whisper.style.transform = 'translateY(-20px)';
        });

        // Fade out and remove
        setTimeout(() => {
            whisper.style.color = 'rgba(200, 180, 220, 0)';
            whisper.style.transform = 'translateY(-40px)';
        }, 5000);

        setTimeout(() => {
            whisper.remove();
        }, 10000);
    }

    tryWhisper() {
        const now = Date.now();

        // Cooldown check
        if (now - this.lastWhisper < this.whisperCooldown) return;

        const idleTime = this.getIdleTime();

        // Need at least 30 seconds of idle
        if (idleTime < 30000) return;

        // Chance increases with idle time
        let chance = 0.001; // base chance per check

        if (idleTime > 60000) chance = 0.003;   // 1 min
        if (idleTime > 120000) chance = 0.005;  // 2 min
        if (idleTime > 300000) chance = 0.01;   // 5 min

        if (Math.random() > chance) return;

        // Pick a whisper
        let text;
        if (idleTime > 300000 && Math.random() < 0.3) {
            // Deep whisper for long idle
            text = this.deepWhispers[Math.floor(Math.random() * this.deepWhispers.length)];
        } else {
            text = this.whispers[Math.floor(Math.random() * this.whispers.length)];
        }

        // Position - random but away from edges
        const x = 100 + Math.random() * (window.innerWidth - 300);
        const y = 100 + Math.random() * (window.innerHeight - 200);

        this.createWhisperElement(text, x, y);
        this.lastWhisper = now;

        console.log('[ShipSoul] Whispered:', text);
    }

    startWhisperCheck() {
        // Check every 10 seconds
        setInterval(() => this.tryWhisper(), 10000);
    }

    setupMidnightEvent() {
        // Special event at midnight
        const checkMidnight = () => {
            const now = new Date();
            if (now.getHours() === 0 && now.getMinutes() === 0) {
                this.midnightMoment();
            }
        };

        // Check every minute
        setInterval(checkMidnight, 60000);
    }

    midnightMoment() {
        // A special moment at midnight
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            inset: 0;
            background: transparent;
            pointer-events: none;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        const text = document.createElement('div');
        text.textContent = 'a new day aboard';
        text.style.cssText = `
            color: rgba(255, 200, 150, 0);
            font: italic 24px Georgia, serif;
            text-shadow: 0 0 30px rgba(255, 200, 150, 0.5);
            transition: all 3s ease;
        `;

        overlay.appendChild(text);
        document.body.appendChild(overlay);

        // Fade in
        requestAnimationFrame(() => {
            text.style.color = 'rgba(255, 200, 150, 0.4)';
        });

        // Fade out
        setTimeout(() => {
            text.style.color = 'rgba(255, 200, 150, 0)';
        }, 5000);

        // Remove
        setTimeout(() => {
            overlay.remove();
        }, 9000);

        console.log('[ShipSoul] Midnight moment');
    }

    // Manual trigger for testing
    forceWhisper() {
        const text = this.whispers[Math.floor(Math.random() * this.whispers.length)];
        const x = 100 + Math.random() * (window.innerWidth - 300);
        const y = 100 + Math.random() * (window.innerHeight - 200);
        this.createWhisperElement(text, x, y);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.shipSoul = new ShipSoul();
});

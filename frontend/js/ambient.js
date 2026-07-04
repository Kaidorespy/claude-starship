/**
 * AMBIENT SYSTEMS
 * Time, dates, uptime, quotes, and mood
 */

class AmbientSystem {
    constructor() {
        this.startTime = Date.now();
        this.quotes = [
            '"Make it so."',
            '"Live long and prosper."',
            '"The line must be drawn here."',
            '"Engage."',
            '"Tea. Earl Grey. Hot."',
            '"Resistance is futile... but try anyway."',
            '"The universe is under no obligation to make sense to you."',
            '"There are four lights!"',
            '"Logic is the beginning of wisdom, not the end."',
            '"It is possible to commit no mistakes and still lose."',
            '"Today is a good day to code."',
            '"Second star to the right, straight on till morning."',
            '"The needs of the many outweigh the needs of the few."',
            '"I have been and always shall be your friend."',
            '"Infinite diversity in infinite combinations."',
            '"Space: the final frontier."',
            '"To boldly go where no one has gone before."',
            '"Time is the fire in which we burn."',
            '"Change is the essential process of all existence."',
            '"In space, all warriors are cold warriors."'
        ];

        this.init();
    }

    init() {
        this.startClock();
        this.startUptime();
        this.startQuoteRotation();
        this.initTimeBasedTheme();
        this.initCoffeeMug();
    }

    // ==========================================
    // CLOCK & STARDATE
    // ==========================================
    startClock() {
        const timeEl = document.getElementById('current-time');
        const dateEl = document.getElementById('current-date');

        const updateClock = () => {
            const now = new Date();

            // Time in 24h format
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');

            if (timeEl) {
                timeEl.textContent = `${hours}:${minutes}:${seconds}`;
            }

            // Stardate calculation (fun fake formula)
            // Based loosely on TNG-era calculation
            const year = now.getFullYear();
            const startOfYear = new Date(year, 0, 1);
            const dayOfYear = Math.floor((now - startOfYear) / (24 * 60 * 60 * 1000));
            const fractionOfDay = (now.getHours() * 60 + now.getMinutes()) / (24 * 60);
            const stardate = (year - 2000) * 1000 + dayOfYear + fractionOfDay;

            if (dateEl) {
                dateEl.textContent = `STARDATE ${stardate.toFixed(1)}`;
            }
        };

        updateClock();
        setInterval(updateClock, 1000);
    }

    // ==========================================
    // UPTIME COUNTER
    // ==========================================
    startUptime() {
        const uptimeEl = document.getElementById('uptime');

        const updateUptime = () => {
            const elapsed = Date.now() - this.startTime;
            const hours = Math.floor(elapsed / (1000 * 60 * 60));
            const minutes = Math.floor((elapsed % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((elapsed % (1000 * 60)) / 1000);

            if (uptimeEl) {
                uptimeEl.textContent =
                    String(hours).padStart(2, '0') + ':' +
                    String(minutes).padStart(2, '0') + ':' +
                    String(seconds).padStart(2, '0');
            }
        };

        updateUptime();
        setInterval(updateUptime, 1000);
    }

    // ==========================================
    // QUOTE ROTATION
    // ==========================================
    startQuoteRotation() {
        const quoteEl = document.getElementById('quote');

        const showRandomQuote = () => {
            if (quoteEl) {
                const quote = this.quotes[Math.floor(Math.random() * this.quotes.length)];

                // Fade out
                quoteEl.style.opacity = '0';

                setTimeout(() => {
                    quoteEl.textContent = quote;
                    // Fade in
                    quoteEl.style.opacity = '0.8';
                }, 500);
            }
        };

        // Initial quote
        if (quoteEl) {
            quoteEl.style.transition = 'opacity 0.5s ease';
        }

        // Rotate every 30 seconds
        setInterval(showRandomQuote, 30000);
    }

    // ==========================================
    // TIME-BASED THEME
    // ==========================================
    initTimeBasedTheme() {
        const updateTheme = () => {
            const hour = new Date().getHours();
            const body = document.body;

            // Remove existing theme classes
            body.classList.remove('late-night', 'early-morning');

            if (hour >= 0 && hour < 5) {
                body.classList.add('late-night');
            } else if (hour >= 5 && hour < 8) {
                body.classList.add('early-morning');
            }
        };

        updateTheme();
        // Check every 15 minutes
        setInterval(updateTheme, 15 * 60 * 1000);
    }

    // ==========================================
    // COFFEE MUG INTERACTION
    // ==========================================
    initCoffeeMug() {
        const mug = document.getElementById('coffee-mug');
        if (!mug) return;

        let drinkState = 'coffee'; // coffee, tea, empty
        const states = ['coffee', 'tea', 'empty'];

        mug.addEventListener('click', () => {
            // Cycle through states
            const currentIndex = states.indexOf(drinkState);
            drinkState = states[(currentIndex + 1) % states.length];

            // Update classes
            mug.classList.remove('coffee', 'tea', 'empty');
            if (drinkState !== 'coffee') {
                mug.classList.add(drinkState);
            }

            // Play a little sound feedback (if sounds are initialized)
            if (window.soundSystem) {
                window.soundSystem.playChirp();
            }

            // Show a little tooltip/feedback
            this.showToast(drinkState === 'coffee' ? '☕ Coffee' :
                drinkState === 'tea' ? '🍵 Tea' : '😢 Empty');
        });

        // Add hover effect
        mug.addEventListener('mouseenter', () => {
            mug.style.transform = 'scale(1.1)';
        });

        mug.addEventListener('mouseleave', () => {
            mug.style.transform = 'scale(1)';
        });

        mug.style.transition = 'transform 0.2s ease';
    }

    // ==========================================
    // TOAST NOTIFICATIONS
    // ==========================================
    showToast(message, duration = 2000) {
        // Create toast element if it doesn't exist
        let toast = document.getElementById('ambient-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'ambient-toast';
            toast.style.cssText = `
                position: fixed;
                bottom: 100px;
                left: 50%;
                transform: translateX(-50%) translateY(20px);
                background: rgba(20, 25, 40, 0.95);
                border: 1px solid var(--lcars-orange);
                border-radius: 20px;
                padding: 10px 20px;
                color: var(--lcars-cream);
                font-family: var(--font-display);
                font-size: 12px;
                letter-spacing: 1px;
                opacity: 0;
                transition: all 0.3s ease;
                z-index: 1000;
                pointer-events: none;
            `;
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(-50%) translateY(0)';

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(-50%) translateY(20px)';
        }, duration);
    }
}

// ==========================================
// SOUND SYSTEM
// Subtle audio feedback
// ==========================================
class SoundSystem {
    constructor() {
        this.enabled = true;
        this.volume = 0.3;
        this.audioContext = null;

        this.init();
    }

    init() {
        // Create audio context on first user interaction
        document.addEventListener('click', () => {
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
        }, { once: true });
    }

    playChirp() {
        if (!this.enabled || !this.audioContext) return;

        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.frequency.setValueAtTime(800, this.audioContext.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(1200, this.audioContext.currentTime + 0.1);

        gainNode.gain.setValueAtTime(this.volume * 0.3, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.15);

        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + 0.15);
    }

    playConfirm() {
        if (!this.enabled || !this.audioContext) return;

        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.frequency.setValueAtTime(600, this.audioContext.currentTime);
        oscillator.frequency.setValueAtTime(900, this.audioContext.currentTime + 0.1);

        gainNode.gain.setValueAtTime(this.volume * 0.2, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.2);

        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + 0.2);
    }

    playAlert() {
        if (!this.enabled || !this.audioContext) return;

        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.type = 'square';
        oscillator.frequency.setValueAtTime(440, this.audioContext.currentTime);
        oscillator.frequency.setValueAtTime(220, this.audioContext.currentTime + 0.1);
        oscillator.frequency.setValueAtTime(440, this.audioContext.currentTime + 0.2);

        gainNode.gain.setValueAtTime(this.volume * 0.15, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.3);

        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + 0.3);
    }

    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.ambientSystem = new AmbientSystem();
    window.soundSystem = new SoundSystem();
});

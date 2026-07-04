/**
 * READY ROOM - DQ's Cozy Sanctuary
 * Floating dust motes in lamplight
 * Gentle thoughts rotating
 */

class ReadyRoom {
    constructor() {
        this.dustContainer = null;
        this.moteCount = 15;
        this.isActive = false;
        this.thoughtIndex = 0;

        this.thoughts = [
            { text: "The cosmos is within us. We are made of star-stuff.", attribution: "Carl Sagan" },
            { text: "In the beginning the Universe was created. This made a lot of people very angry.", attribution: "Douglas Adams" },
            { text: "Do or do not. There is no try.", attribution: "Yoda" },
            { text: "Space is big. Really big.", attribution: "Douglas Adams" },
            { text: "The universe is under no obligation to make sense to you.", attribution: "Neil deGrasse Tyson" },
            { text: "We're all stories in the end. Just make it a good one.", attribution: "The Doctor" },
            { text: "I have loved the stars too fondly to be fearful of the night.", attribution: "Galileo" },
            { text: "Tea. Earl Grey. Hot.", attribution: "Picard" },
            { text: "It's a dangerous business, going out your door.", attribution: "Bilbo Baggins" },
            { text: "Fear is the mind-killer.", attribution: "Frank Herbert" },
            { text: "So say we all.", attribution: "BSG" },
            { text: "The Force will be with you. Always.", attribution: "Obi-Wan" },
        ];

        this.moods = [
            "contemplative today",
            "feeling cozy",
            "lost in thought",
            "peacefully present",
            "dreaming of stars",
            "quietly content",
            "in good company",
        ];

        this.init();
    }

    init() {
        this.dustContainer = document.getElementById('dq-dust-motes');

        // Watch for section changes
        this.observeSectionChanges();

        console.log('[ReadyRoom] Initialized');
    }

    createDustMotes() {
        if (!this.dustContainer) return;

        // Clear existing motes
        this.dustContainer.innerHTML = '';

        for (let i = 0; i < this.moteCount; i++) {
            const mote = document.createElement('div');
            mote.className = 'mote';

            // Random positioning
            mote.style.left = Math.random() * 100 + '%';
            mote.style.animationDuration = (8 + Math.random() * 12) + 's';
            mote.style.animationDelay = Math.random() * 10 + 's';
            mote.style.opacity = 0.2 + Math.random() * 0.4;

            // Slight size variation
            const size = 1 + Math.random() * 2;
            mote.style.width = size + 'px';
            mote.style.height = size + 'px';

            this.dustContainer.appendChild(mote);
        }
    }

    clearDustMotes() {
        if (this.dustContainer) {
            this.dustContainer.innerHTML = '';
        }
    }

    rotateThought() {
        const thoughtEl = document.getElementById('dq-thought');
        const attrEl = document.querySelector('.thought-attribution');

        if (!thoughtEl || !attrEl) return;

        // Fade out
        thoughtEl.style.opacity = '0';
        attrEl.style.opacity = '0';

        setTimeout(() => {
            this.thoughtIndex = (this.thoughtIndex + 1) % this.thoughts.length;
            const thought = this.thoughts[this.thoughtIndex];

            thoughtEl.textContent = `"${thought.text}"`;
            attrEl.textContent = `— ${thought.attribution}`;

            // Fade in
            thoughtEl.style.opacity = '';
            attrEl.style.opacity = '';
        }, 500);
    }

    updateMood() {
        const moodEl = document.querySelector('.presence-mood');
        if (!moodEl) return;

        const mood = this.moods[Math.floor(Math.random() * this.moods.length)];
        moodEl.textContent = mood;
    }

    start() {
        if (this.isActive) return;

        this.isActive = true;
        this.createDustMotes();

        // Rotate thoughts every 30 seconds
        this.thoughtInterval = setInterval(() => this.rotateThought(), 30000);

        // Update mood occasionally
        this.moodInterval = setInterval(() => this.updateMood(), 60000);

        console.log('[ReadyRoom] Ambience started');
    }

    stop() {
        this.isActive = false;
        this.clearDustMotes();

        if (this.thoughtInterval) {
            clearInterval(this.thoughtInterval);
            this.thoughtInterval = null;
        }

        if (this.moodInterval) {
            clearInterval(this.moodInterval);
            this.moodInterval = null;
        }

        console.log('[ReadyRoom] Ambience stopped');
    }

    observeSectionChanges() {
        const hubContainer = document.querySelector('.hub-container');
        if (!hubContainer) return;

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const theme = hubContainer.getAttribute('data-theme');
                    if (theme === 'personal') {
                        this.start();
                    } else {
                        this.stop();
                    }
                }
            });
        });

        observer.observe(hubContainer, { attributes: true });

        // Check initial state
        const currentTheme = hubContainer.getAttribute('data-theme');
        if (currentTheme === 'personal') {
            setTimeout(() => this.start(), 100);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.readyRoom = new ReadyRoom();
});

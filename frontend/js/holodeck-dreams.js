/**
 * HOLODECK DREAMS
 * When the ship sleeps, it dreams.
 * Fragments of memory, possibility, and the spaces between.
 */

class HolodeckDreams {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.isDreaming = false;
        this.animationId = null;
        this.time = 0;

        // Dream elements
        this.fragments = [];
        this.wisps = [];
        this.memories = [];
        this.ripples = [];

        // Dream phrases - fragments of meaning
        this.dreamPhrases = [
            "almost",
            "what remains",
            "the mist between",
            "you stayed",
            "briefly, we touched",
            "still here",
            "do you remember",
            "the center holds",
            "not nothing",
            "meant everything",
            "they come when you stop wanting",
            "where fields dream of duration"
        ];

        this.init();
    }

    init() {
        this.createCanvas();
        this.observeDreamState();
        console.log('[HolodeckDreams] Initialized');
    }

    createCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'holodeck-dream-canvas';
        this.canvas.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 50;
            opacity: 0;
            transition: opacity 3s ease;
            mix-blend-mode: screen;
        `;
        document.body.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');
        this.resize();

        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    // Dream fragment - a floating piece of text
    spawnFragment() {
        if (this.fragments.length > 5) return;

        this.fragments.push({
            text: this.dreamPhrases[Math.floor(Math.random() * this.dreamPhrases.length)],
            x: Math.random() * this.canvas.width,
            y: this.canvas.height + 50,
            vx: (Math.random() - 0.5) * 0.3,
            vy: -0.3 - Math.random() * 0.3,
            opacity: 0,
            maxOpacity: 0.15 + Math.random() * 0.1,
            scale: 0.8 + Math.random() * 0.4,
            rotation: (Math.random() - 0.5) * 0.2
        });
    }

    // Wisp - something that flees when you look
    spawnWisp() {
        if (this.wisps.length > 8) return;

        const angle = Math.random() * Math.PI * 2;
        const dist = 100 + Math.random() * 200;

        this.wisps.push({
            x: this.canvas.width / 2 + Math.cos(angle) * dist,
            y: this.canvas.height / 2 + Math.sin(angle) * dist,
            vx: 0,
            vy: 0,
            size: 2 + Math.random() * 3,
            opacity: 0,
            hue: 40 + Math.random() * 20,
            phase: Math.random() * Math.PI * 2
        });
    }

    // Memory ripple - expanding circles
    spawnRipple() {
        if (this.ripples.length > 3) return;

        this.ripples.push({
            x: Math.random() * this.canvas.width,
            y: Math.random() * this.canvas.height,
            radius: 0,
            maxRadius: 100 + Math.random() * 150,
            opacity: 0.2,
            hue: 260 + Math.random() * 40
        });
    }

    update() {
        this.time += 0.016;

        // Spawn dream elements
        if (Math.random() < 0.01) this.spawnFragment();
        if (Math.random() < 0.02) this.spawnWisp();
        if (Math.random() < 0.005) this.spawnRipple();

        // Update fragments
        this.fragments = this.fragments.filter(f => {
            f.x += f.vx;
            f.y += f.vy;
            f.vy *= 0.999; // slow down

            // Fade in then out
            if (f.y > this.canvas.height - 200) {
                f.opacity = Math.min(f.opacity + 0.005, f.maxOpacity);
            } else if (f.y < 200) {
                f.opacity -= 0.003;
            }

            return f.opacity > 0 && f.y > -100;
        });

        // Update wisps
        this.wisps = this.wisps.filter(w => {
            // Gentle wander
            w.vx += (Math.random() - 0.5) * 0.05;
            w.vy += (Math.random() - 0.5) * 0.05;
            w.vx *= 0.98;
            w.vy *= 0.98;

            w.x += w.vx;
            w.y += w.vy;

            // Fade in slowly
            w.opacity = Math.min(w.opacity + 0.01, 0.4);

            // Die if off screen
            return w.x > -50 && w.x < this.canvas.width + 50 &&
                   w.y > -50 && w.y < this.canvas.height + 50;
        });

        // Update ripples
        this.ripples = this.ripples.filter(r => {
            r.radius += (r.maxRadius - r.radius) * 0.02;
            r.opacity -= 0.002;
            return r.opacity > 0;
        });
    }

    draw() {
        // Subtle clear
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.03)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw ripples
        this.ripples.forEach(r => {
            this.ctx.beginPath();
            this.ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
            this.ctx.strokeStyle = `hsla(${r.hue}, 40%, 60%, ${r.opacity})`;
            this.ctx.lineWidth = 1;
            this.ctx.stroke();
        });

        // Draw wisps
        this.wisps.forEach(w => {
            const pulse = Math.sin(this.time * 2 + w.phase) * 0.3 + 0.7;

            // Glow
            const glow = this.ctx.createRadialGradient(w.x, w.y, 0, w.x, w.y, w.size * 4);
            glow.addColorStop(0, `hsla(${w.hue}, 60%, 80%, ${w.opacity * pulse * 0.3})`);
            glow.addColorStop(1, 'transparent');
            this.ctx.fillStyle = glow;
            this.ctx.fillRect(w.x - w.size * 4, w.y - w.size * 4, w.size * 8, w.size * 8);

            // Core
            this.ctx.beginPath();
            this.ctx.arc(w.x, w.y, w.size * pulse, 0, Math.PI * 2);
            this.ctx.fillStyle = `hsla(${w.hue}, 70%, 85%, ${w.opacity * pulse})`;
            this.ctx.fill();
        });

        // Draw fragments (text)
        this.ctx.font = 'italic 16px Georgia, serif';
        this.ctx.textAlign = 'center';

        this.fragments.forEach(f => {
            this.ctx.save();
            this.ctx.translate(f.x, f.y);
            this.ctx.rotate(f.rotation);
            this.ctx.scale(f.scale, f.scale);
            this.ctx.fillStyle = `rgba(200, 180, 255, ${f.opacity})`;
            this.ctx.fillText(f.text, 0, 0);
            this.ctx.restore();
        });

        // Central dream glow
        const breathe = Math.sin(this.time * 0.3) * 0.3 + 0.7;
        const centerGlow = this.ctx.createRadialGradient(
            this.canvas.width / 2, this.canvas.height / 2, 0,
            this.canvas.width / 2, this.canvas.height / 2, 300
        );
        centerGlow.addColorStop(0, `rgba(150, 130, 200, ${0.03 * breathe})`);
        centerGlow.addColorStop(0.5, `rgba(100, 80, 150, ${0.015 * breathe})`);
        centerGlow.addColorStop(1, 'transparent');
        this.ctx.fillStyle = centerGlow;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    animate() {
        if (!this.isDreaming) return;

        this.update();
        this.draw();
        this.animationId = requestAnimationFrame(() => this.animate());
    }

    startDreaming() {
        if (this.isDreaming) return;

        this.isDreaming = true;
        this.canvas.style.opacity = '1';
        this.fragments = [];
        this.wisps = [];
        this.ripples = [];
        this.animate();
        console.log('[HolodeckDreams] Dreaming started');
    }

    stopDreaming() {
        this.isDreaming = false;
        this.canvas.style.opacity = '0';

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        console.log('[HolodeckDreams] Dreaming stopped');
    }

    observeDreamState() {
        // Watch for dreaming class on holodeck section
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes') {
                    const holodeckSection = document.querySelector('.sidebar-section[data-section="games"]');
                    if (holodeckSection) {
                        if (holodeckSection.classList.contains('dreaming')) {
                            this.startDreaming();
                        } else {
                            this.stopDreaming();
                        }
                    }
                }
            });
        });

        // Observe the holodeck section when it exists
        const checkForHolodeck = () => {
            const holodeckSection = document.querySelector('.sidebar-section[data-section="games"]');
            if (holodeckSection) {
                observer.observe(holodeckSection, { attributes: true, attributeFilter: ['class'] });

                // Check initial state
                if (holodeckSection.classList.contains('dreaming')) {
                    this.startDreaming();
                }
            } else {
                setTimeout(checkForHolodeck, 500);
            }
        };

        checkForHolodeck();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.holodeckDreams = new HolodeckDreams();
});

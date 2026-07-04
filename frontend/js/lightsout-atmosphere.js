/**
 * LIGHTS OUT ATMOSPHERE
 * When the ship sleeps, the stars breathe deeper.
 * A meditation space, a reflection pool.
 */

class LightsOutAtmosphere {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.isActive = false;
        this.animationId = null;
        this.time = 0;

        // Floating thoughts
        this.motes = [];
        this.reflections = [];

        this.init();
    }

    init() {
        this.createCanvas();
        this.observeTheme();
        console.log('[LightsOutAtmosphere] Initialized');
    }

    createCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'lightsout-atmosphere';
        this.canvas.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
            opacity: 0;
            transition: opacity 3s ease;
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

    initElements() {
        this.motes = [];
        this.reflections = [];

        // Floating motes - like dust in moonlight
        for (let i = 0; i < 30; i++) {
            this.motes.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: 0.5 + Math.random() * 1.5,
                speed: 0.1 + Math.random() * 0.2,
                phase: Math.random() * Math.PI * 2,
                opacity: 0.1 + Math.random() * 0.2
            });
        }

        // Reflection pools - gentle light areas
        for (let i = 0; i < 3; i++) {
            this.reflections.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: 100 + Math.random() * 200,
                phase: Math.random() * Math.PI * 2,
                hue: 220 + Math.random() * 40
            });
        }
    }

    update() {
        this.time += 0.008; // Slower than normal

        // Update motes
        this.motes.forEach(m => {
            m.y -= m.speed;
            m.x += Math.sin(this.time + m.phase) * 0.2;

            // Reset at top
            if (m.y < -10) {
                m.y = this.canvas.height + 10;
                m.x = Math.random() * this.canvas.width;
            }
        });

        // Slowly drift reflections
        this.reflections.forEach(r => {
            r.x += Math.sin(this.time * 0.3 + r.phase) * 0.1;
            r.y += Math.cos(this.time * 0.2 + r.phase) * 0.05;
        });
    }

    draw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw reflections first
        this.reflections.forEach(r => {
            const breathe = Math.sin(this.time * 0.5 + r.phase) * 0.3 + 0.7;
            const gradient = this.ctx.createRadialGradient(
                r.x, r.y, 0,
                r.x, r.y, r.radius * breathe
            );
            gradient.addColorStop(0, `hsla(${r.hue}, 30%, 40%, 0.03)`);
            gradient.addColorStop(0.5, `hsla(${r.hue}, 25%, 30%, 0.015)`);
            gradient.addColorStop(1, 'transparent');

            this.ctx.fillStyle = gradient;
            this.ctx.fillRect(r.x - r.radius, r.y - r.radius, r.radius * 2, r.radius * 2);
        });

        // Draw motes
        this.motes.forEach(m => {
            const pulse = Math.sin(this.time * 2 + m.phase) * 0.3 + 0.7;

            this.ctx.beginPath();
            this.ctx.arc(m.x, m.y, m.size * pulse, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(150, 170, 220, ${m.opacity * pulse})`;
            this.ctx.fill();

            // Tiny glow
            this.ctx.beginPath();
            this.ctx.arc(m.x, m.y, m.size * 3, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(150, 170, 220, ${m.opacity * 0.1 * pulse})`;
            this.ctx.fill();
        });

        // Central calm
        const centerBreath = Math.sin(this.time * 0.3) * 0.2 + 0.8;
        const centerGlow = this.ctx.createRadialGradient(
            this.canvas.width / 2, this.canvas.height / 2, 0,
            this.canvas.width / 2, this.canvas.height / 2, 400
        );
        centerGlow.addColorStop(0, `rgba(100, 120, 180, ${0.02 * centerBreath})`);
        centerGlow.addColorStop(1, 'transparent');
        this.ctx.fillStyle = centerGlow;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    animate() {
        if (!this.isActive) return;

        this.update();
        this.draw();
        this.animationId = requestAnimationFrame(() => this.animate());
    }

    start() {
        if (this.isActive) return;

        this.isActive = true;
        this.initElements();
        this.canvas.style.opacity = '1';
        this.animate();
        console.log('[LightsOutAtmosphere] Started');
    }

    stop() {
        this.isActive = false;
        this.canvas.style.opacity = '0';

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        console.log('[LightsOutAtmosphere] Stopped');
    }

    observeTheme() {
        // Watch for theme changes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const theme = document.body.getAttribute('data-theme') ||
                                  document.querySelector('.hub-container')?.getAttribute('data-theme');

                    if (theme === 'lightsout') {
                        setTimeout(() => this.start(), 500); // Slight delay for theme transition
                    } else {
                        this.stop();
                    }
                }
            });
        });

        // Observe both body and hub-container
        observer.observe(document.body, { attributes: true });

        const hubContainer = document.querySelector('.hub-container');
        if (hubContainer) {
            observer.observe(hubContainer, { attributes: true });
        }

        // Also check on load after a delay
        setTimeout(() => {
            const theme = document.body.getAttribute('data-theme') ||
                          document.querySelector('.hub-container')?.getAttribute('data-theme');
            if (theme === 'lightsout') {
                this.start();
            }
        }, 1000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.lightsOutAtmosphere = new LightsOutAtmosphere();
});

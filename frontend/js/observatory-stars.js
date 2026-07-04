/**
 * OBSERVATORY STARFIELD
 * The view from the window. Depth, breath, infinity.
 * A collaboration between Claude and Casey.
 */

class ObservatoryStars {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.stars = [];
        this.nebulaClouds = [];
        this.shootingStars = [];
        this.time = 0;
        this.isActive = false;
        this.animationId = null;

        // Parallax layers
        this.layers = [
            { count: 200, speed: 0.02, sizeRange: [0.3, 0.8], opacity: 0.3 },  // far
            { count: 150, speed: 0.05, sizeRange: [0.5, 1.2], opacity: 0.5 },  // mid
            { count: 80, speed: 0.1, sizeRange: [1, 2], opacity: 0.8 },        // near
            { count: 20, speed: 0.15, sizeRange: [1.5, 2.5], opacity: 1 }      // foreground
        ];

        this.init();
    }

    init() {
        this.createCanvas();
        this.initStars();
        this.initNebula();
        this.setupThemeObserver();
        console.log('Observatory stars initialized');
    }

    createCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'observatory-starfield';
        this.canvas.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0;
            transition: opacity 1.5s ease;
        `;
        document.body.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');
        this.resize();

        // Debounce resize to prevent jitter during window resizing
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => this.resize(), 100);
        });
    }

    resize() {
        const oldWidth = this.canvas.width;
        const oldHeight = this.canvas.height;
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;

        // Reposition stars if canvas size changed significantly while active
        if (this.isActive && (oldWidth !== this.canvas.width || oldHeight !== this.canvas.height)) {
            this.initStars();
            this.initNebula();
        }
    }

    initStars() {
        this.stars = [];

        this.layers.forEach((layer, layerIndex) => {
            for (let i = 0; i < layer.count; i++) {
                this.stars.push({
                    x: Math.random() * this.canvas.width,
                    y: Math.random() * this.canvas.height,
                    baseSize: layer.sizeRange[0] + Math.random() * (layer.sizeRange[1] - layer.sizeRange[0]),
                    layer: layerIndex,
                    speed: layer.speed,
                    opacity: layer.opacity * (0.5 + Math.random() * 0.5),
                    twinklePhase: Math.random() * Math.PI * 2,
                    twinkleSpeed: 0.5 + Math.random() * 1.5,
                    hue: Math.random() < 0.1 ? (Math.random() < 0.5 ? 200 : 30) : 0, // some blue, some gold
                    saturation: Math.random() < 0.1 ? 30 : 0
                });
            }
        });
    }

    initNebula() {
        this.nebulaClouds = [];

        // Create soft nebula patches
        const colors = [
            { h: 270, s: 30, l: 15 },  // purple
            { h: 200, s: 25, l: 12 },  // blue
            { h: 30, s: 20, l: 10 },   // warm
            { h: 320, s: 20, l: 10 }   // magenta
        ];

        for (let i = 0; i < 5; i++) {
            const color = colors[Math.floor(Math.random() * colors.length)];
            this.nebulaClouds.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: 150 + Math.random() * 250,
                color: color,
                phase: Math.random() * Math.PI * 2,
                drift: {
                    x: (Math.random() - 0.5) * 0.1,
                    y: (Math.random() - 0.5) * 0.1
                }
            });
        }
    }

    spawnShootingStar() {
        if (Math.random() > 0.002) return; // rare

        this.shootingStars.push({
            x: Math.random() * this.canvas.width,
            y: Math.random() * this.canvas.height * 0.5,
            vx: 3 + Math.random() * 4,
            vy: 1 + Math.random() * 2,
            life: 1,
            length: 30 + Math.random() * 50
        });
    }

    update() {
        this.time += 0.016;

        // Spawn shooting stars
        this.spawnShootingStar();

        // Update shooting stars
        this.shootingStars = this.shootingStars.filter(s => {
            s.x += s.vx;
            s.y += s.vy;
            s.life -= 0.02;
            return s.life > 0 && s.x < this.canvas.width + 100;
        });

        // Drift nebula
        this.nebulaClouds.forEach(cloud => {
            cloud.x += cloud.drift.x;
            cloud.y += cloud.drift.y;

            // Wrap
            if (cloud.x < -cloud.radius) cloud.x = this.canvas.width + cloud.radius;
            if (cloud.x > this.canvas.width + cloud.radius) cloud.x = -cloud.radius;
            if (cloud.y < -cloud.radius) cloud.y = this.canvas.height + cloud.radius;
            if (cloud.y > this.canvas.height + cloud.radius) cloud.y = -cloud.radius;
        });
    }

    draw() {
        // Clear with deep space
        this.ctx.fillStyle = '#050508';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw nebula first (behind stars)
        this.drawNebula();

        // Draw stars by layer (far to near)
        for (let layerIndex = 0; layerIndex < this.layers.length; layerIndex++) {
            this.stars
                .filter(s => s.layer === layerIndex)
                .forEach(star => this.drawStar(star));
        }

        // Draw shooting stars
        this.shootingStars.forEach(s => this.drawShootingStar(s));
    }

    drawNebula() {
        this.nebulaClouds.forEach(cloud => {
            const breathe = Math.sin(this.time * 0.3 + cloud.phase) * 0.2 + 0.8;
            const gradient = this.ctx.createRadialGradient(
                cloud.x, cloud.y, 0,
                cloud.x, cloud.y, cloud.radius * breathe
            );

            const { h, s, l } = cloud.color;
            gradient.addColorStop(0, `hsla(${h}, ${s}%, ${l}%, 0.08)`);
            gradient.addColorStop(0.4, `hsla(${h}, ${s}%, ${l}%, 0.04)`);
            gradient.addColorStop(1, 'transparent');

            this.ctx.fillStyle = gradient;
            this.ctx.fillRect(
                cloud.x - cloud.radius,
                cloud.y - cloud.radius,
                cloud.radius * 2,
                cloud.radius * 2
            );
        });
    }

    drawStar(star) {
        const twinkle = Math.sin(this.time * star.twinkleSpeed + star.twinklePhase) * 0.3 + 0.7;
        const size = star.baseSize * twinkle;
        const opacity = star.opacity * twinkle;

        // Star glow
        if (star.layer >= 2) {
            const glowSize = size * 4;
            const glow = this.ctx.createRadialGradient(
                star.x, star.y, 0,
                star.x, star.y, glowSize
            );
            glow.addColorStop(0, `hsla(${star.hue}, ${star.saturation}%, 100%, ${opacity * 0.15})`);
            glow.addColorStop(1, 'transparent');
            this.ctx.fillStyle = glow;
            this.ctx.fillRect(star.x - glowSize, star.y - glowSize, glowSize * 2, glowSize * 2);
        }

        // Star core
        this.ctx.beginPath();
        this.ctx.arc(star.x, star.y, size, 0, Math.PI * 2);
        this.ctx.fillStyle = `hsla(${star.hue}, ${star.saturation}%, 100%, ${opacity})`;
        this.ctx.fill();
    }

    drawShootingStar(star) {
        const gradient = this.ctx.createLinearGradient(
            star.x, star.y,
            star.x - star.vx * star.length / 5, star.y - star.vy * star.length / 5
        );
        gradient.addColorStop(0, `rgba(255, 255, 255, ${star.life})`);
        gradient.addColorStop(1, 'transparent');

        this.ctx.strokeStyle = gradient;
        this.ctx.lineWidth = 1.5;
        this.ctx.beginPath();
        this.ctx.moveTo(star.x, star.y);
        this.ctx.lineTo(star.x - star.vx * star.length / 5, star.y - star.vy * star.length / 5);
        this.ctx.stroke();

        // Head glow
        this.ctx.beginPath();
        this.ctx.arc(star.x, star.y, 2, 0, Math.PI * 2);
        this.ctx.fillStyle = `rgba(255, 255, 255, ${star.life})`;
        this.ctx.fill();
    }

    animate() {
        if (!this.isActive) return;

        this.update();
        this.draw();
        this.animationId = requestAnimationFrame(() => this.animate());
    }

    show() {
        this.isActive = true;
        this.resize();
        this.initStars();  // Reinitialize stars for current canvas size
        this.initNebula(); // Reinitialize nebula too
        this.canvas.style.opacity = '1';
        this.animate();
    }

    hide() {
        this.isActive = false;
        this.canvas.style.opacity = '0';
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    setupThemeObserver() {
        // Watch for theme changes on body
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const theme = document.body.getAttribute('data-theme');
                    if (theme === 'observatory') {
                        this.show();
                    } else {
                        this.hide();
                    }
                }
            });
        });

        observer.observe(document.body, { attributes: true });

        // Check initial state
        const currentTheme = document.body.getAttribute('data-theme');
        if (currentTheme === 'observatory') {
            this.show();
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.observatoryStars = new ObservatoryStars();
});

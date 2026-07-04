/**
 * MEDBAY - Medical Bay Systems
 * Heartbeat monitor and vitals
 */

class MedbaySystem {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.animationId = null;
        this.isActive = false;

        // Heartbeat settings
        this.heartbeatData = [];
        this.maxDataPoints = 100;
        this.currentX = 0;
        this.bpm = 72;
        this.lastBeat = 0;
        this.beatInterval = 60000 / this.bpm; // ms between beats

        this.init();
    }

    init() {
        this.canvas = document.getElementById('heartbeat-canvas');
        if (!this.canvas) {
            console.debug('[Medbay] Canvas not found');
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.resize();

        // Watch for section changes
        this.observeSectionChanges();

        // Handle resize
        window.addEventListener('resize', () => this.resize());

        console.log('[Medbay] Initialized');
    }

    resize() {
        if (!this.canvas) return;

        const container = this.canvas.parentElement;
        if (!container) return;

        this.canvas.width = container.offsetWidth;
        this.canvas.height = container.offsetHeight;

        // Reset data on resize
        this.heartbeatData = [];
        this.currentX = 0;
    }

    generateHeartbeatPoint(progress) {
        // Create realistic ECG-like pattern
        const baseY = this.canvas.height / 2;
        const amplitude = this.canvas.height * 0.35;

        // Different phases of heartbeat
        if (progress < 0.1) {
            // P wave (small bump)
            return baseY - Math.sin(progress * Math.PI / 0.1) * amplitude * 0.15;
        } else if (progress < 0.2) {
            // Flat
            return baseY;
        } else if (progress < 0.25) {
            // Q dip
            return baseY + (progress - 0.2) / 0.05 * amplitude * 0.1;
        } else if (progress < 0.35) {
            // R spike (main peak)
            const rProgress = (progress - 0.25) / 0.1;
            if (rProgress < 0.5) {
                return baseY - rProgress * 2 * amplitude * 0.9;
            } else {
                return baseY - (1 - (rProgress - 0.5) * 2) * amplitude * 0.9;
            }
        } else if (progress < 0.4) {
            // S dip
            return baseY + (1 - (progress - 0.35) / 0.05) * amplitude * 0.2;
        } else if (progress < 0.6) {
            // Flat
            return baseY;
        } else if (progress < 0.8) {
            // T wave (rounded bump)
            const tProgress = (progress - 0.6) / 0.2;
            return baseY - Math.sin(tProgress * Math.PI) * amplitude * 0.25;
        } else {
            // Flat until next beat
            return baseY;
        }
    }

    animate(timestamp) {
        if (!this.isActive || !this.ctx) return;

        // Clear canvas with fade effect
        this.ctx.fillStyle = 'rgba(20, 15, 25, 0.15)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Check if it's time for a new beat
        if (timestamp - this.lastBeat > this.beatInterval) {
            this.lastBeat = timestamp;
            // Slight BPM variation for realism
            this.bpm = 70 + Math.random() * 8;
            this.beatInterval = 60000 / this.bpm;
            this.updateBpmDisplay();
        }

        // Calculate progress through current beat cycle
        const beatProgress = (timestamp - this.lastBeat) / this.beatInterval;

        // Add new point
        const y = this.generateHeartbeatPoint(beatProgress);
        this.heartbeatData.push(y);

        // Keep data within bounds
        if (this.heartbeatData.length > this.maxDataPoints) {
            this.heartbeatData.shift();
        }

        // Draw the line
        this.drawHeartbeat();

        this.animationId = requestAnimationFrame((t) => this.animate(t));
    }

    drawHeartbeat() {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const pointSpacing = width / this.maxDataPoints;

        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 102, 153, 0.8)';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        for (let i = 0; i < this.heartbeatData.length; i++) {
            const x = i * pointSpacing;
            const y = this.heartbeatData[i];

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }

        ctx.stroke();

        // Glow effect
        ctx.strokeStyle = 'rgba(255, 102, 153, 0.3)';
        ctx.lineWidth = 6;
        ctx.stroke();
    }

    updateBpmDisplay() {
        const display = document.getElementById('heartbeat-value');
        if (display) {
            display.textContent = Math.round(this.bpm);
        }
    }

    start() {
        if (this.isActive) return;

        this.isActive = true;
        this.resize();
        this.heartbeatData = [];
        this.lastBeat = performance.now();

        // Clear canvas
        if (this.ctx) {
            this.ctx.fillStyle = 'rgba(20, 15, 25, 1)';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        }

        this.animationId = requestAnimationFrame((t) => this.animate(t));
        console.log('[Medbay] Animation started');
    }

    stop() {
        this.isActive = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        console.log('[Medbay] Animation stopped');
    }

    observeSectionChanges() {
        const hubContainer = document.querySelector('.hub-container');
        if (!hubContainer) return;

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const theme = hubContainer.getAttribute('data-theme');
                    if (theme === 'med') {
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
        if (currentTheme === 'med') {
            setTimeout(() => this.start(), 100);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.medbaySystem = new MedbaySystem();
});

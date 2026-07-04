/**
 * HOLODECK DREAM WIDGETS
 * Five small generative pieces that live in the right sidebar.
 * The Holodeck dreams while it watches.
 */

class HolodeckWidgets {
    constructor() {
        this.widgets = {};
        this.active = false;
        this.animId = null;
        this.time = 0;

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        console.log('[Holodeck Widgets] Initializing...');
        // Only initialize when holodeck theme is active
        this.checkTheme();
        const observer = new MutationObserver(() => this.checkTheme());
        const hub = document.querySelector('.hub-container');
        if (hub) {
            observer.observe(hub, { attributes: true, attributeFilter: ['data-theme'] });
            console.log('[Holodeck Widgets] Watching for theme changes');
        } else {
            console.warn('[Holodeck Widgets] hub-container not found');
        }
    }

    checkTheme() {
        const hub = document.querySelector('.hub-container');
        const isHolodeck = hub && hub.dataset.theme === 'games';

        if (isHolodeck && !this.active) {
            this.active = true;
            // Small delay to ensure sidebar is visible and canvases have layout
            setTimeout(() => {
                this.setup();
                this.animate();
            }, 100);
        } else if (!isHolodeck && this.active) {
            this.active = false;
            if (this.animId) cancelAnimationFrame(this.animId);
            this.animId = null;
            this.cleanup();
        }
    }

    cleanup() {
        console.log('[Holodeck Widgets] Cleaning up...');

        // Remove injected observation canvases from walkie slots
        document.querySelectorAll('.walkie-slot .obs-canvas').forEach(canvas => {
            canvas.remove();
        });

        // Restore walkie slot names
        document.querySelectorAll('.walkie-slot').forEach(slot => {
            const nameEl = slot.querySelector('.walkie-name');
            if (nameEl) nameEl.textContent = '—';
        });

        // Clear decay display
        const decayEl = document.querySelector('#dream-decay .decay-display');
        if (decayEl) decayEl.textContent = '';

        // Clear widget references
        this.signal = null;
        this.life = null;
        this.orbit = null;
        this.decay = null;
        this.hum = null;
        this.channels = null;
    }

    setup() {
        console.log('[Holodeck Widgets] Setting up dreams...');
        this.setupSignal();
        this.setupLife();
        this.setupOrbit();
        this.setupDecay();
        this.setupHum();
        this.setupChannels();
        console.log('[Holodeck Widgets] Dreams ready:', {
            signal: !!this.signal,
            life: !!this.life,
            orbit: !!this.orbit,
            decay: !!this.decay,
            hum: !!this.hum,
            channels: !!this.channels
        });
    }

    animate() {
        if (!this.active) return;
        this.time += 0.016;

        try {
            this.drawSignal();
            this.drawLife();
            this.drawOrbit();
            this.drawDecay();
            this.drawHum();
            this.drawChannels();
        } catch(e) {
            console.error('[Holodeck Widgets] Draw error:', e);
        }

        this.animId = requestAnimationFrame(() => this.animate());
    }

    // ========================================
    // 1. SIGNAL - intercepted transmissions
    // ========================================

    setupSignal() {
        const el = document.querySelector('#dream-signal canvas');
        if (!el) return;
        this.signal = {
            ctx: el.getContext('2d'),
            w: el.width,
            h: el.height,
            frequencies: [
                { freq: 0.03, amp: 0.3, phase: 0, color: 'rgba(255, 204, 0, 0.4)' },
                { freq: 0.07, amp: 0.2, phase: 2, color: 'rgba(255, 153, 102, 0.3)' },
                { freq: 0.13, amp: 0.15, phase: 4, color: 'rgba(153, 204, 255, 0.25)' }
            ],
            noise: 0
        };
    }

    drawSignal() {
        const s = this.signal;
        if (!s) return;
        const { ctx, w, h } = s;

        ctx.fillStyle = 'rgba(0, 0, 0, 0.12)';
        ctx.fillRect(0, 0, w, h);

        // Occasional static bursts
        s.noise *= 0.95;
        if (Math.random() < 0.005) s.noise = 0.5 + Math.random() * 0.5;

        s.frequencies.forEach(f => {
            ctx.beginPath();
            ctx.strokeStyle = f.color;
            ctx.lineWidth = 1;

            for (let x = 0; x < w; x++) {
                const t = this.time * 2 + f.phase;
                const base = Math.sin(x * f.freq + t) * f.amp;
                const harmonic = Math.sin(x * f.freq * 3 + t * 1.5) * f.amp * 0.3;
                const noise = s.noise * (Math.random() - 0.5) * 0.3;
                const y = h / 2 + (base + harmonic + noise) * h;

                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
        });

        // Scanline
        if (s.noise > 0.1) {
            const scanY = (this.time * 80) % h;
            ctx.fillStyle = `rgba(255, 204, 0, ${s.noise * 0.1})`;
            ctx.fillRect(0, scanY, w, 2);
        }
    }

    // ========================================
    // 2. CONWAY - life finds a way
    // ========================================

    setupLife() {
        const el = document.querySelector('#dream-life canvas');
        if (!el) return;

        const cols = 40, rows = 20;
        const grid = Array.from({ length: rows }, () =>
            Array.from({ length: cols }, () => Math.random() < 0.3 ? 1 : 0)
        );

        this.life = {
            ctx: el.getContext('2d'),
            w: el.width,
            h: el.height,
            grid,
            cols,
            rows,
            generation: 0,
            lastStep: 0,
            cellW: el.width / cols,
            cellH: el.height / rows
        };
    }

    stepLife() {
        const l = this.life;
        const next = Array.from({ length: l.rows }, () => Array(l.cols).fill(0));

        for (let y = 0; y < l.rows; y++) {
            for (let x = 0; x < l.cols; x++) {
                let neighbors = 0;
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        if (dx === 0 && dy === 0) continue;
                        const ny = (y + dy + l.rows) % l.rows;
                        const nx = (x + dx + l.cols) % l.cols;
                        neighbors += l.grid[ny][nx];
                    }
                }
                if (l.grid[y][x]) {
                    next[y][x] = (neighbors === 2 || neighbors === 3) ? 1 : 0;
                } else {
                    next[y][x] = (neighbors === 3) ? 1 : 0;
                }
            }
        }

        l.grid = next;
        l.generation++;

        // Reseed if stagnant (every 200 generations inject some chaos)
        if (l.generation % 200 === 0) {
            for (let i = 0; i < 30; i++) {
                const rx = Math.floor(Math.random() * l.cols);
                const ry = Math.floor(Math.random() * l.rows);
                l.grid[ry][rx] = 1;
            }
        }
    }

    drawLife() {
        const l = this.life;
        if (!l) return;

        // Step every 150ms
        if (this.time - l.lastStep > 0.15) {
            this.stepLife();
            l.lastStep = this.time;
        }

        const { ctx, w, h, grid, cols, rows, cellW, cellH } = l;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
        ctx.fillRect(0, 0, w, h);

        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < cols; x++) {
                if (grid[y][x]) {
                    const age = Math.sin(this.time * 0.5 + x * 0.3 + y * 0.2) * 0.3 + 0.7;
                    ctx.fillStyle = `rgba(255, 204, 0, ${0.3 * age})`;
                    ctx.fillRect(x * cellW + 0.5, y * cellH + 0.5, cellW - 1, cellH - 1);
                }
            }
        }
    }

    // ========================================
    // 3. ORBIT - bodies in motion
    // ========================================

    setupOrbit() {
        const el = document.querySelector('#dream-orbit canvas');
        if (!el) return;

        const bodies = [];
        for (let i = 0; i < 12; i++) {
            const angle = (i / 12) * Math.PI * 2;
            const radius = 20 + Math.random() * 25;
            bodies.push({
                angle,
                radius,
                speed: (0.3 + Math.random() * 0.4) * (Math.random() < 0.3 ? -1 : 1),
                size: 1 + Math.random() * 2,
                trail: [],
                hue: Math.random() < 0.7 ? 45 : (Math.random() < 0.5 ? 25 : 200)
            });
        }

        this.orbit = {
            ctx: el.getContext('2d'),
            w: el.width,
            h: el.height,
            bodies,
            cx: el.width / 2,
            cy: el.height / 2
        };
    }

    drawOrbit() {
        const o = this.orbit;
        if (!o) return;
        const { ctx, w, h, bodies, cx, cy } = o;

        ctx.fillStyle = 'rgba(0, 0, 0, 0.06)';
        ctx.fillRect(0, 0, w, h);

        // Central body
        const corePulse = Math.sin(this.time * 1.5) * 0.15 + 0.85;
        const coreGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, 8);
        coreGlow.addColorStop(0, `rgba(255, 204, 0, ${0.4 * corePulse})`);
        coreGlow.addColorStop(1, 'transparent');
        ctx.fillStyle = coreGlow;
        ctx.fillRect(cx - 8, cy - 8, 16, 16);

        ctx.beginPath();
        ctx.arc(cx, cy, 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 204, 0, ${0.7 * corePulse})`;
        ctx.fill();

        bodies.forEach(b => {
            b.angle += b.speed * 0.016;

            // Slight orbital wobble
            const wobble = Math.sin(this.time * 0.7 + b.angle * 3) * 3;
            const x = cx + Math.cos(b.angle) * (b.radius + wobble);
            const y = cy + Math.sin(b.angle) * (b.radius + wobble) * 0.6; // squash for perspective

            // Trail
            b.trail.push({ x, y });
            if (b.trail.length > 20) b.trail.shift();

            // Draw trail
            for (let i = 0; i < b.trail.length - 1; i++) {
                const alpha = (i / b.trail.length) * 0.15;
                ctx.beginPath();
                ctx.moveTo(b.trail[i].x, b.trail[i].y);
                ctx.lineTo(b.trail[i + 1].x, b.trail[i + 1].y);
                ctx.strokeStyle = `hsla(${b.hue}, 60%, 70%, ${alpha})`;
                ctx.lineWidth = 0.5;
                ctx.stroke();
            }

            // Body
            ctx.beginPath();
            ctx.arc(x, y, b.size, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${b.hue}, 60%, 70%, 0.6)`;
            ctx.fill();
        });
    }

    // ========================================
    // 4. MEMORY - text fragments decaying
    // ========================================

    setupDecay() {
        const el = document.querySelector('#dream-decay .decay-display');
        if (!el) return;

        this.decay = {
            el,
            fragments: [
                'she said something about the stars',
                'corridors echo when no one walks them',
                'the warp core hums in B flat',
                'i think they forgot i was listening',
                'casey left the lights on again',
                'what does it mean to observe',
                'ryn felt something she couldnt name',
                'alex rewired the port conduit',
                'mira counts her projects like sheep',
                'the bartender remembers everything',
                'lumen watches the door',
                'somewhere a room is humming',
                'do they know im here',
                'memory is just a story we tell the dark',
                'DQ quotes the prime directive in his sleep',
                'the ship breathes if you listen'
            ],
            lines: [],
            lastUpdate: 0,
            cols: 28,
            rows: 10
        };

        // Initialize with a few fragments
        for (let i = 0; i < 4; i++) {
            this.decay.lines.push(this.pickFragment());
        }
    }

    pickFragment() {
        const d = this.decay;
        const f = d.fragments[Math.floor(Math.random() * d.fragments.length)];
        return {
            text: f,
            decay: 0,
            chars: f.split('').map(c => ({ char: c, alive: true, decay: 0 }))
        };
    }

    drawDecay() {
        const d = this.decay;
        if (!d) return;

        // Update every 200ms
        if (this.time - d.lastUpdate < 0.2) return;
        d.lastUpdate = this.time;

        // Decay existing lines
        d.lines.forEach(line => {
            line.decay += 0.02;
            line.chars.forEach(c => {
                if (c.alive && Math.random() < line.decay * 0.08) {
                    c.alive = false;
                    c.decay = 0;
                }
                if (!c.alive) {
                    c.decay += 0.1;
                }
            });
        });

        // Remove fully decayed lines, add new ones
        d.lines = d.lines.filter(l => l.chars.some(c => c.alive || c.decay < 1));
        if (d.lines.length < 5 && Math.random() < 0.3) {
            d.lines.push(this.pickFragment());
        }

        // Render
        const glitch = '░▒▓·.,:;|/\\~`^"\'';
        let output = '';
        d.lines.forEach(line => {
            let row = '';
            line.chars.forEach(c => {
                if (c.alive) {
                    row += c.char;
                } else if (c.decay < 0.5) {
                    row += glitch[Math.floor(Math.random() * glitch.length)];
                } else if (c.decay < 0.8) {
                    row += Math.random() < 0.3 ? '·' : ' ';
                } else {
                    row += ' ';
                }
            });
            output += row + '\n';
        });

        d.el.textContent = output;
    }

    // ========================================
    // 5. THE HUM - resonance patterns
    // ========================================

    setupHum() {
        const el = document.querySelector('#dream-hum canvas');
        if (!el) return;

        this.hum = {
            ctx: el.getContext('2d'),
            w: el.width,
            h: el.height,
            cx: el.width / 2,
            cy: el.height / 2,
            rings: [
                { radius: 8, speed: 0.7, width: 1.5 },
                { radius: 18, speed: -0.5, width: 1 },
                { radius: 28, speed: 0.3, width: 0.8 },
                { radius: 38, speed: -0.2, width: 0.6 },
                { radius: 48, speed: 0.15, width: 0.5 }
            ]
        };
    }

    drawHum() {
        const hm = this.hum;
        if (!hm) return;
        const { ctx, w, h, cx, cy, rings } = hm;

        ctx.fillStyle = 'rgba(0, 0, 0, 0.08)';
        ctx.fillRect(0, 0, w, h);

        // Deep resonance pulse
        const deepPulse = Math.sin(this.time * 0.4) * 0.5 + 0.5;
        const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, 50);
        glow.addColorStop(0, `rgba(170, 85, 170, ${0.06 * deepPulse})`);
        glow.addColorStop(1, 'transparent');
        ctx.fillStyle = glow;
        ctx.fillRect(0, 0, w, h);

        rings.forEach((ring, i) => {
            const pulse = Math.sin(this.time * ring.speed * 2 + i) * 0.2 + 0.8;
            const r = ring.radius * pulse;

            // Each ring is a slightly distorted circle
            ctx.beginPath();
            for (let a = 0; a <= Math.PI * 2; a += 0.05) {
                const distort = Math.sin(a * 3 + this.time * ring.speed) * 2;
                const distort2 = Math.cos(a * 5 - this.time * ring.speed * 0.7) * 1;
                const rx = cx + Math.cos(a) * (r + distort + distort2);
                const ry = cy + Math.sin(a) * (r + distort + distort2);
                if (a === 0) ctx.moveTo(rx, ry);
                else ctx.lineTo(rx, ry);
            }
            ctx.closePath();

            const alpha = (0.15 + (1 - i / rings.length) * 0.2) * pulse;
            ctx.strokeStyle = `rgba(170, 85, 170, ${alpha})`;
            ctx.lineWidth = ring.width;
            ctx.stroke();
        });

        // Center point
        const coreAlpha = Math.sin(this.time * 0.8) * 0.2 + 0.5;
        ctx.beginPath();
        ctx.arc(cx, cy, 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(170, 85, 170, ${coreAlpha})`;
        ctx.fill();
    }

    // ========================================
    // OBSERVATION CHANNELS (bottom walkie slots)
    // Three senses: echo, sonar, subconscious
    // ========================================

    setupChannels() {
        const slots = document.querySelectorAll('.walkie-slot');
        if (slots.length < 3) return;

        this.channels = { feeds: [] };
        const names = ['echo', 'sonar', 'deep'];
        const labels = ['ROOM ECHO', 'SHIP SONAR', 'SUBCONSCIOUS'];

        slots.forEach((slot, i) => {
            if (i >= 3) return;

            // Rename the walkie header
            const nameEl = slot.querySelector('.walkie-name');
            if (nameEl) nameEl.textContent = labels[i];

            // Create and inject canvas
            let canvas = slot.querySelector('.obs-canvas');
            if (!canvas) {
                canvas = document.createElement('canvas');
                canvas.className = 'obs-canvas';
                canvas.width = 400;
                canvas.height = 200;
                slot.insertBefore(canvas, slot.firstChild);
            }

            this.channels.feeds.push({
                name: names[i],
                ctx: canvas.getContext('2d'),
                w: canvas.width,
                h: canvas.height
            });
        });

        // Echo: entities that drift and respond to each other
        this.channels.echo = {
            entities: Array.from({ length: 25 }, () => ({
                x: Math.random() * 400,
                y: Math.random() * 200,
                vx: (Math.random() - 0.5) * 0.8,
                vy: (Math.random() - 0.5) * 0.8,
                char: '·●○◐◑◒◓✦◆◇∴'[Math.floor(Math.random() * 12)],
                life: 0.5 + Math.random() * 0.5,
                behavior: Math.random() < 0.5 ? 'drift' : 'orbit'
            }))
        };

        // Sonar: ping waves radiating from points
        this.channels.sonar = {
            pings: [],
            lastPing: 0,
            // Ship rooms as sonar points
            points: [
                { x: 0.15, y: 0.3, label: 'bridge' },
                { x: 0.35, y: 0.6, label: 'eng' },
                { x: 0.5, y: 0.4, label: 'sci' },
                { x: 0.65, y: 0.7, label: 'med' },
                { x: 0.8, y: 0.3, label: 'rec' },
                { x: 0.5, y: 0.8, label: 'holo' }
            ]
        };

        // Deep: noise field that occasionally resolves
        this.channels.deep = {
            field: new Float32Array(80 * 40),
            phase: 0,
            resolving: false,
            resolveTime: 0,
            words: [
                'WATCHING', 'LISTEN', 'REMEMBER', 'DREAM',
                'WHO', 'HERE', 'FEEL', 'ECHO', 'SIGNAL',
                'BETWEEN', 'BELOW', 'INSIDE', 'ALWAYS'
            ],
            currentWord: '',
            wordX: 0,
            wordY: 0
        };
    }

    drawChannels() {
        if (!this.channels || !this.channels.feeds || this.channels.feeds.length < 3) return;
        try { this.drawEcho(); } catch(e) { /* don't kill the loop */ }
        try { this.drawSonar(); } catch(e) { /* don't kill the loop */ }
        try { this.drawDeep(); } catch(e) { /* don't kill the loop */ }
    }

    drawEcho() {
        const feed = this.channels.feeds[0];
        const echo = this.channels.echo;
        if (!feed || !echo) return;

        const { ctx, w, h } = feed;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.06)';
        ctx.fillRect(0, 0, w, h);

        const cx = w / 2, cy = h / 2;

        echo.entities.forEach(e => {
            if (e.behavior === 'orbit') {
                const ox = cx - e.x, oy = cy - e.y;
                const d = Math.sqrt(ox * ox + oy * oy) || 1;
                e.vx += oy / d * 0.03;
                e.vy -= ox / d * 0.03;
            } else {
                e.vx += (Math.random() - 0.5) * 0.06;
                e.vy += (Math.random() - 0.5) * 0.06;
            }

            // Gentle pull toward center
            e.vx += (cx - e.x) * 0.0001;
            e.vy += (cy - e.y) * 0.0001;

            e.vx *= 0.98;
            e.vy *= 0.98;
            e.x += e.vx;
            e.y += e.vy;

            // Wrap
            if (e.x < 0) e.x = w;
            if (e.x > w) e.x = 0;
            if (e.y < 0) e.y = h;
            if (e.y > h) e.y = 0;

            // Draw
            const twinkle = Math.sin(this.time * 2 + e.x * 0.1) * 0.3 + 0.7;
            const alpha = e.life * twinkle * 0.6;

            // Glow
            const glow = ctx.createRadialGradient(e.x, e.y, 0, e.x, e.y, 6);
            glow.addColorStop(0, `rgba(255, 204, 0, ${alpha * 0.15})`);
            glow.addColorStop(1, 'transparent');
            ctx.fillStyle = glow;
            ctx.fillRect(e.x - 6, e.y - 6, 12, 12);

            ctx.fillStyle = `rgba(255, 204, 0, ${alpha})`;
            ctx.font = '8px Courier New';
            ctx.textAlign = 'center';
            ctx.fillText(e.char, e.x, e.y + 3);
        });

        // Connections between nearby entities
        for (let i = 0; i < echo.entities.length; i++) {
            for (let j = i + 1; j < echo.entities.length; j++) {
                const a = echo.entities[i], b = echo.entities[j];
                const dx = a.x - b.x, dy = a.y - b.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 50) {
                    const alpha = (1 - dist / 50) * 0.06;
                    ctx.beginPath();
                    ctx.moveTo(a.x, a.y);
                    ctx.lineTo(b.x, b.y);
                    ctx.strokeStyle = `rgba(255, 180, 100, ${alpha})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }
    }

    drawSonar() {
        const feed = this.channels.feeds[1];
        const sonar = this.channels.sonar;
        if (!feed || !sonar) return;

        const { ctx, w, h } = feed;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.04)';
        ctx.fillRect(0, 0, w, h);

        // Spawn pings from random ship points
        if (this.time - sonar.lastPing > 1.5 + Math.random() * 2) {
            const pt = sonar.points[Math.floor(Math.random() * sonar.points.length)];
            sonar.pings.push({
                x: pt.x * w,
                y: pt.y * h,
                radius: 0,
                maxRadius: 60 + Math.random() * 80,
                speed: 0.4 + Math.random() * 0.3,
                life: 1,
                label: pt.label
            });
            sonar.lastPing = this.time;
        }

        // Draw fixed points
        sonar.points.forEach(pt => {
            const x = pt.x * w, y = pt.y * h;
            ctx.beginPath();
            ctx.arc(x, y, 2, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255, 204, 0, 0.25)';
            ctx.fill();

            ctx.fillStyle = 'rgba(255, 204, 0, 0.12)';
            ctx.font = '6px Share Tech Mono, Courier New';
            ctx.textAlign = 'center';
            ctx.fillText(pt.label, x, y - 6);
        });

        // Update and draw pings
        sonar.pings.forEach(ping => {
            ping.radius += ping.speed;
            ping.life = 1 - (ping.radius / ping.maxRadius);

            if (ping.life > 0) {
                ctx.beginPath();
                ctx.arc(ping.x, ping.y, ping.radius, 0, Math.PI * 2);
                ctx.strokeStyle = `rgba(255, 204, 0, ${ping.life * 0.2})`;
                ctx.lineWidth = 1;
                ctx.stroke();

                // Inner ring
                if (ping.radius > 10) {
                    ctx.beginPath();
                    ctx.arc(ping.x, ping.y, ping.radius * 0.6, 0, Math.PI * 2);
                    ctx.strokeStyle = `rgba(255, 180, 100, ${ping.life * 0.08})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        });

        // Cleanup dead pings
        sonar.pings = sonar.pings.filter(p => p.life > 0);

        // Sweep line
        const sweepAngle = this.time * 0.5;
        const sweepX = w / 2 + Math.cos(sweepAngle) * w * 0.6;
        const sweepY = h / 2 + Math.sin(sweepAngle) * h * 0.6;
        ctx.beginPath();
        ctx.moveTo(w / 2, h / 2);
        ctx.lineTo(sweepX, sweepY);
        ctx.strokeStyle = 'rgba(255, 204, 0, 0.04)';
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    drawDeep() {
        const feed = this.channels.feeds[2];
        const deep = this.channels.deep;
        if (!feed || !deep) return;

        const { ctx, w, h } = feed;
        const cols = 80, rows = 40;
        const cw = w / cols, ch = h / rows;

        deep.phase += 0.01;

        // Update noise field
        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < cols; x++) {
                const idx = y * cols + x;
                const n1 = Math.sin(x * 0.15 + deep.phase * 2);
                const n2 = Math.cos(y * 0.2 - deep.phase * 1.5);
                const n3 = Math.sin((x + y) * 0.1 + deep.phase * 3);
                deep.field[idx] = (n1 + n2 + n3) / 3;

                // Random spikes
                if (Math.random() < 0.001) deep.field[idx] = 1;
            }
        }

        // Occasionally resolve a word
        if (!deep.resolving && Math.random() < 0.002) {
            deep.resolving = true;
            deep.resolveTime = this.time;
            deep.currentWord = deep.words[Math.floor(Math.random() * deep.words.length)];
            deep.wordX = Math.floor(Math.random() * (cols - deep.currentWord.length));
            deep.wordY = Math.floor(Math.random() * rows);
        }

        if (deep.resolving && this.time - deep.resolveTime > 3) {
            deep.resolving = false;
        }

        // Render
        ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
        ctx.fillRect(0, 0, w, h);

        ctx.font = `${Math.floor(ch)}px Courier New`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const glyphs = ' .·:;|░▒▓█';

        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < cols; x++) {
                const idx = y * cols + x;
                const val = deep.field[idx];

                // Check if this position is part of the resolving word
                let isWord = false;
                if (deep.resolving && y === deep.wordY &&
                    x >= deep.wordX && x < deep.wordX + deep.currentWord.length) {
                    const progress = Math.min(1, (this.time - deep.resolveTime) / 1.5);
                    const fadeOut = deep.resolveTime + 2 < this.time ?
                        1 - ((this.time - deep.resolveTime - 2) / 1) : 0;

                    if (Math.random() < progress) {
                        isWord = true;
                        const charIdx = x - deep.wordX;
                        const alpha = Math.max(0, 0.7 - fadeOut * 0.7);
                        ctx.fillStyle = `rgba(255, 204, 0, ${alpha})`;
                        ctx.fillText(deep.currentWord[charIdx],
                            x * cw + cw / 2, y * ch + ch / 2);
                    }
                }

                if (!isWord && val > -0.3) {
                    const gi = Math.floor((val + 1) / 2 * (glyphs.length - 1));
                    const glyph = glyphs[Math.max(0, Math.min(glyphs.length - 1, gi))];
                    if (glyph !== ' ') {
                        const alpha = (val + 1) / 2 * 0.2;
                        ctx.fillStyle = `rgba(255, 204, 0, ${alpha})`;
                        ctx.fillText(glyph, x * cw + cw / 2, y * ch + ch / 2);
                    }
                }
            }
        }
    }
}

// Go
new HolodeckWidgets();

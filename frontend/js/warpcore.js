/**
 * WARP CORE - Particle Animation
 * Matter and antimatter converging on the reaction chamber
 */

class WarpCore {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.particleCount = 80;
        this.centerX = 0;
        this.centerY = 0;
        this.pulsePhase = 0;
        this.animationId = null;
        this.isActive = false;

        this.init();
    }

    init() {
        this.canvas = document.getElementById('warp-core-canvas');
        if (!this.canvas) {
            console.debug('[WarpCore] Canvas not found');
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.resize();
        this.initParticles();

        // Start animation when Engineering section becomes active
        this.observeSectionChanges();

        // Handle resize
        window.addEventListener('resize', () => this.resize());

        console.log('[WarpCore] Initialized');
    }

    resize() {
        if (!this.canvas) return;

        const container = this.canvas.parentElement;
        if (!container) return;

        this.canvas.width = container.offsetWidth;
        this.canvas.height = container.offsetHeight;

        this.centerX = this.canvas.width / 2;
        this.centerY = this.canvas.height / 2;
    }

    initParticles() {
        this.particles = [];
        for (let i = 0; i < this.particleCount; i++) {
            this.particles.push(this.createParticle());
        }
    }

    createParticle() {
        // Spawn in a ring around center, will drift inward
        const angle = Math.random() * Math.PI * 2;
        const distance = Math.random() * 100 + 60;

        return {
            x: this.centerX + Math.cos(angle) * distance,
            y: this.centerY + Math.sin(angle) * distance,
            targetX: this.centerX,
            targetY: this.centerY,
            life: 0,
            maxLife: Math.random() * 150 + 80,
            size: Math.random() * 2 + 0.5,
            hue: Math.random() * 40 + 180, // Cyan range (180-220)
            speed: 0.015 + Math.random() * 0.01
        };
    }

    updateParticle(p) {
        p.life++;

        // Ease toward center
        p.x += (p.targetX - p.x) * p.speed;
        p.y += (p.targetY - p.y) * p.speed;

        // Reset when life ends or reaches center
        const distToCenter = Math.sqrt(
            Math.pow(p.x - this.centerX, 2) + Math.pow(p.y - this.centerY, 2)
        );

        if (p.life >= p.maxLife || distToCenter < 10) {
            Object.assign(p, this.createParticle());
        }
    }

    drawParticle(p) {
        const progress = p.life / p.maxLife;

        // Fade in and out
        let alpha;
        if (progress < 0.15) {
            alpha = progress / 0.15;
        } else if (progress > 0.85) {
            alpha = (1 - progress) / 0.15;
        } else {
            alpha = 1;
        }

        // Distance to center affects brightness
        const distToCenter = Math.sqrt(
            Math.pow(p.x - this.centerX, 2) + Math.pow(p.y - this.centerY, 2)
        );

        // Brighter as it gets closer
        const proximityBoost = distToCenter < 40 ? (1 - distToCenter / 40) * 0.5 : 0;

        // Draw particle
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        this.ctx.fillStyle = `hsla(${p.hue}, 70%, ${60 + proximityBoost * 30}%, ${(alpha * 0.7) + proximityBoost})`;
        this.ctx.fill();

        // Extra glow when close to center
        if (distToCenter < 30) {
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size * 3, 0, Math.PI * 2);
            this.ctx.fillStyle = `hsla(${p.hue}, 80%, 70%, ${alpha * 0.2})`;
            this.ctx.fill();
        }
    }

    drawConnections() {
        for (let i = 0; i < this.particles.length; i++) {
            for (let j = i + 1; j < this.particles.length; j++) {
                const dx = this.particles[i].x - this.particles[j].x;
                const dy = this.particles[i].y - this.particles[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < 50) {
                    const alpha = (1 - distance / 50) * 0.1;
                    this.ctx.beginPath();
                    this.ctx.moveTo(this.particles[i].x, this.particles[i].y);
                    this.ctx.lineTo(this.particles[j].x, this.particles[j].y);
                    this.ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        }
    }

    drawCoreGlow() {
        this.pulsePhase += 0.03;
        const pulseIntensity = 0.5 + Math.sin(this.pulsePhase) * 0.2;

        // Outer glow
        const gradient = this.ctx.createRadialGradient(
            this.centerX, this.centerY, 0,
            this.centerX, this.centerY, 40
        );
        gradient.addColorStop(0, `rgba(255, 255, 255, ${pulseIntensity})`);
        gradient.addColorStop(0.3, `rgba(0, 212, 255, ${pulseIntensity * 0.4})`);
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');

        this.ctx.beginPath();
        this.ctx.arc(this.centerX, this.centerY, 40, 0, Math.PI * 2);
        this.ctx.fillStyle = gradient;
        this.ctx.fill();
    }

    animate() {
        if (!this.isActive || !this.ctx) return;

        // Fade trail effect
        this.ctx.fillStyle = 'rgba(0, 10, 20, 0.08)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw connections first (behind particles)
        this.drawConnections();

        // Update and draw particles
        this.particles.forEach(p => {
            this.updateParticle(p);
            this.drawParticle(p);
        });

        // Draw core glow
        this.drawCoreGlow();

        this.animationId = requestAnimationFrame(() => this.animate());
    }

    start() {
        if (this.isActive) return;

        this.isActive = true;
        this.resize();

        // Clear canvas
        if (this.ctx) {
            this.ctx.fillStyle = 'rgba(0, 10, 20, 1)';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        }

        this.animate();
        console.log('[WarpCore] Animation started');
    }

    stop() {
        this.isActive = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        console.log('[WarpCore] Animation stopped');
    }

    observeSectionChanges() {
        // Watch for theme changes (section switches)
        const hubContainer = document.querySelector('.hub-container');
        if (!hubContainer) return;

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const theme = hubContainer.getAttribute('data-theme');
                    if (theme === 'servers') {
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
        if (currentTheme === 'servers') {
            // Delay start to ensure DOM is ready
            setTimeout(() => this.start(), 100);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.warpCore = new WarpCore();
});



/**
 * HARDWARE MONITOR - Ship Diagnostics
 * Real-time system stats display for Engineering
 */

class HardwareMonitor {
    constructor() {
        this.pollInterval = null;
        this.pollRate = 2000; // 2 seconds for smoother updates
        this.isActive = false;

        // For calculating rates
        this.lastNetSent = 0;
        this.lastNetRecv = 0;
        this.lastDiskRead = 0;
        this.lastDiskWrite = 0;
        this.lastTime = 0;

        this.init();
    }

    init() {
        this.observeSectionChanges();
        this.setupLhmHint();
        this.setupToolButtons();
        console.log('[HardwareMonitor] Initialized');
    }

    observeSectionChanges() {
        const hubContainer = document.querySelector('.hub-container');
        if (!hubContainer) return;

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const theme = hubContainer.getAttribute('data-theme');
                    if (theme === 'servers') {
                        this.start();
                    } else {
                        this.stop();
                    }
                }
            });
        });

        observer.observe(hubContainer, { attributes: true });

        const currentTheme = hubContainer.getAttribute('data-theme');
        if (currentTheme === 'servers') {
            setTimeout(() => this.start(), 500);
        }
    }

    start() {
        if (this.isActive) return;
        this.isActive = true;
        this.fetchStats();
        this.pollInterval = setInterval(() => this.fetchStats(), this.pollRate);
        console.log('[HardwareMonitor] Started polling');
    }

    stop() {
        this.isActive = false;
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        console.log('[HardwareMonitor] Stopped polling');
    }

    async fetchStats() {
        try {
            const response = await fetch('/system/stats');
            if (!response.ok) throw new Error('Failed to fetch stats');
            const stats = await response.json();
            if (stats.error) {
                console.warn('[HardwareMonitor] Error:', stats.error);
                return;
            }
            this.updateDisplay(stats);
        } catch (err) {
            console.warn('[HardwareMonitor] Fetch failed:', err.message);
        }
    }

    updateDisplay(stats) {
        const now = Date.now();
        const elapsed = this.lastTime > 0 ? (now - this.lastTime) / 1000 : 1;

        // CPU
        this.updateMetric('cpu', stats.cpu.percent, `${stats.cpu.percent}%`);
        this.setText('hw-cpu-cores', `${stats.cpu.cores_logical} cores`);
        this.setText('hw-cpu-freq', stats.cpu.freq_mhz ? `${stats.cpu.freq_mhz} MHz` : '');

        // Per-core CPU
        if (stats.cpu.per_core) {
            this.updateCoresGrid(stats.cpu.per_core);
        }

        // Memory
        this.updateMetric('mem', stats.memory.percent, `${stats.memory.percent}%`);
        this.setText('hw-mem-used', `${stats.memory.used_gb} GB`);
        this.setText('hw-mem-total', `/ ${stats.memory.total_gb} GB`);

        // Swap
        if (stats.swap) {
            this.updateMetric('swap', stats.swap.percent, `${stats.swap.percent}%`);
        }

        // Disk
        this.updateMetric('disk', stats.disk.percent, `${stats.disk.percent}%`);
        this.setText('hw-disk-used', `${stats.disk.used_gb} GB`);
        this.setText('hw-disk-total', `/ ${stats.disk.total_gb} GB`);

        // Disk I/O rates
        if (this.lastDiskRead > 0) {
            const readRate = (stats.disk.read_bytes - this.lastDiskRead) / elapsed;
            const writeRate = (stats.disk.write_bytes - this.lastDiskWrite) / elapsed;
            this.setText('hw-disk-read', this.formatBytes(readRate) + '/s');
            this.setText('hw-disk-write', this.formatBytes(writeRate) + '/s');
        }
        this.lastDiskRead = stats.disk.read_bytes;
        this.lastDiskWrite = stats.disk.write_bytes;

        // Network rates
        if (this.lastNetSent > 0) {
            const sentRate = (stats.network.bytes_sent - this.lastNetSent) / elapsed;
            const recvRate = (stats.network.bytes_recv - this.lastNetRecv) / elapsed;
            this.setText('hw-net-sent', this.formatBytes(sentRate) + '/s');
            this.setText('hw-net-recv', this.formatBytes(recvRate) + '/s');
        }
        this.lastNetSent = stats.network.bytes_sent;
        this.lastNetRecv = stats.network.bytes_recv;

        // Temperatures
        this.updateTemps(stats.temps);

        // Fans
        this.updateFans(stats.fans);

        // Battery
        this.updateBattery(stats.battery);

        // GPU
        this.updateGPU(stats.gpu);

        // System info
        this.setText('hw-uptime', stats.uptime.formatted);
        this.setText('hw-processes', stats.processes.toString());

        this.lastTime = now;

        // Show LHM hint if not available and not dismissed
        this.updateLhmHint(stats.lhm_available);
    }

    updateCoresGrid(perCore) {
        const grid = document.getElementById('hw-cpu-cores-grid');
        if (!grid) return;

        // Create core bars if they don't exist
        if (grid.children.length !== perCore.length) {
            grid.innerHTML = perCore.map((_, i) => `
                <div class="hw-core-bar" title="Core ${i}">
                    <div class="hw-core-fill" id="hw-core-${i}"></div>
                </div>
            `).join('');
        }

        // Update values
        perCore.forEach((percent, i) => {
            const fill = document.getElementById(`hw-core-${i}`);
            if (fill) {
                fill.style.height = `${percent}%`;
                fill.classList.remove('high', 'critical');
                if (percent >= 90) fill.classList.add('critical');
                else if (percent >= 70) fill.classList.add('high');
            }
        });
    }

    updateTemps(temps) {
        const section = document.getElementById('hw-temps-section');
        const grid = document.getElementById('hw-temps-grid');
        if (!section || !grid) return;

        if (!temps || Object.keys(temps).length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';

        let html = '';
        for (const [name, sensors] of Object.entries(temps)) {
            sensors.forEach(sensor => {
                const tempClass = sensor.current >= (sensor.critical || 90) ? 'hot' :
                                  sensor.current >= (sensor.high || 70) ? 'warm' : '';
                html += `
                    <div class="hw-temp-item">
                        <span class="hw-temp-label">${sensor.label || name}</span>
                        <span class="hw-temp-value ${tempClass}">${sensor.current.toFixed(0)}°C</span>
                    </div>
                `;
            });
        }
        grid.innerHTML = html;
    }

    updateFans(fans) {
        const section = document.getElementById('hw-fans-section');
        const grid = document.getElementById('hw-fans-grid');
        if (!section || !grid) return;

        if (!fans || Object.keys(fans).length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';

        let html = '';
        for (const [name, fanList] of Object.entries(fans)) {
            fanList.forEach(fan => {
                const fastClass = fan.rpm > 2000 ? 'fast' : '';
                html += `
                    <div class="hw-fan-item">
                        <span class="hw-fan-icon ${fastClass}">&#9788;</span>
                        <span class="hw-fan-label">${fan.label || name}</span>
                        <span class="hw-fan-value">${fan.rpm} RPM</span>
                    </div>
                `;
            });
        }
        grid.innerHTML = html;
    }

    updateBattery(battery) {
        const section = document.getElementById('hw-battery-section');
        if (!section) return;

        if (!battery) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';

        const bar = document.getElementById('hw-battery-bar');
        const percentEl = document.getElementById('hw-battery-percent');
        const statusEl = document.getElementById('hw-battery-status');
        const timeEl = document.getElementById('hw-battery-time');

        if (bar) {
            bar.style.width = `${battery.percent}%`;
            bar.classList.remove('low', 'critical');
            if (battery.percent <= 10) bar.classList.add('critical');
            else if (battery.percent <= 25) bar.classList.add('low');
        }

        if (percentEl) percentEl.textContent = `${battery.percent}%`;
        if (statusEl) statusEl.textContent = battery.plugged ? 'CHARGING' : 'DISCHARGING';

        if (timeEl && battery.seconds_left) {
            const hours = Math.floor(battery.seconds_left / 3600);
            const mins = Math.floor((battery.seconds_left % 3600) / 60);
            timeEl.textContent = `${hours}h ${mins}m`;
        } else if (timeEl) {
            timeEl.textContent = battery.plugged ? 'AC POWER' : '';
        }
    }

    updateMetric(type, percent, valueText) {
        const bar = document.getElementById(`hw-${type}-bar`);
        const value = document.getElementById(`hw-${type}-percent`);

        if (bar) {
            bar.style.width = `${percent}%`;
            bar.classList.remove('warning', 'critical');
            if (percent >= 90) bar.classList.add('critical');
            else if (percent >= 75) bar.classList.add('warning');
        }

        if (value) value.textContent = valueText;
    }

    setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    updateGPU(gpu) {
        const section = document.getElementById("hw-gpu-section");
        if (!section) return;

        if (!gpu) {
            section.style.display = "none";
            return;
        }

        section.style.display = "block";

        const nameEl = document.getElementById("hw-gpu-name");
        if (nameEl) nameEl.textContent = gpu.name || "GPU";

        const tempEl = document.getElementById("hw-gpu-temp");
        if (tempEl && gpu.temps && gpu.temps.length > 0) {
            const temp = gpu.temps[0].value;
            tempEl.textContent = temp.toFixed(0) + "°C";
            tempEl.classList.toggle("hot", temp >= 80);
        }

        const loadEl = document.getElementById("hw-gpu-load");
        if (loadEl && gpu.loads && gpu.loads.length > 0) {
            const coreLoad = gpu.loads.find(l => l.name.includes("Core")) || gpu.loads[0];
            loadEl.textContent = coreLoad.value.toFixed(0) + "%";
        }

        const clockEl = document.getElementById("hw-gpu-clock");
        if (clockEl && gpu.clocks && gpu.clocks.length > 0) {
            const coreClock = gpu.clocks.find(c => c.name.includes("Core")) || gpu.clocks[0];
            clockEl.textContent = coreClock.value.toFixed(0) + " MHz";
        }

        const fanEl = document.getElementById("hw-gpu-fan");
        if (fanEl && gpu.fans && gpu.fans.length > 0) {
            fanEl.textContent = gpu.fans[0].value.toFixed(0) + " RPM";
        } else if (fanEl) {
            fanEl.textContent = "--";
        }
    }


    setupLhmHint() {
        const dismissBtn = document.getElementById('hw-hint-dismiss');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', () => {
                localStorage.setItem('hw-lhm-hint-dismissed', 'true');
                const hint = document.getElementById('hw-lhm-hint');
                if (hint) hint.style.display = 'none';
            });
        }


        const launchBtn = document.getElementById('hw-hint-launch');
        if (launchBtn) {
            launchBtn.addEventListener('click', async () => {
                launchBtn.classList.add('loading');
                launchBtn.textContent = '...';
                try {
                    const resp = await fetch('/system/launch-lhm', { method: 'POST' });
                    const result = await resp.json();
                    if (result.success) {
                        launchBtn.textContent = 'Launched!';
                        setTimeout(() => {
                            launchBtn.textContent = 'Enable';
                            launchBtn.classList.remove('loading');
                        }, 5000);
                    } else {
                        launchBtn.textContent = 'Not found';
                        console.warn('[HW] Launch failed:', result.error);
                        setTimeout(() => {
                            launchBtn.textContent = 'Enable';
                            launchBtn.classList.remove('loading');
                        }, 3000);
                    }
                } catch (err) {
                    launchBtn.textContent = 'Error';
                    setTimeout(() => {
                        launchBtn.textContent = 'Enable';
                        launchBtn.classList.remove('loading');
                    }, 3000);
                }
            });
        }
    }

    updateLhmHint(lhmAvailable) {
        const hint = document.getElementById('hw-lhm-hint');
        if (!hint) return;

        // Don't show if already dismissed
        if (localStorage.getItem('hw-lhm-hint-dismissed') === 'true') {
            hint.style.display = 'none';
            return;
        }

        // Show hint only if LHM is not available
        hint.style.display = lhmAvailable ? 'none' : 'block';
    }


    setupToolButtons() {
        const diskhogBtn = document.getElementById('hw-diskhog-btn');
        if (diskhogBtn) {
            diskhogBtn.addEventListener('click', async () => {
                diskhogBtn.textContent = 'Launching...';
                try {
                    const resp = await fetch('/system/launch-diskhog', { method: 'POST' });
                    const result = await resp.json();
                    if (result.success) {
                        diskhogBtn.textContent = 'DiskHog';
                    } else {
                        diskhogBtn.textContent = 'Not found';
                        setTimeout(() => diskhogBtn.textContent = 'DiskHog', 3000);
                    }
                } catch (err) {
                    diskhogBtn.textContent = 'Error';
                    setTimeout(() => diskhogBtn.textContent = 'DiskHog', 3000);
                }
            });
        }
    }

    formatBytes(bytes) {
        if (bytes < 1024) return bytes.toFixed(0) + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.hardwareMonitor = new HardwareMonitor();
});

/**
 * DECORATIVE TECHNOBABBLE
 * All the gorgeous nonsense that makes it feel like a real spaceship
 */

class DecorativeEngine {
    constructor() {
        this.waveformCanvas = document.getElementById('waveform-canvas');
        this.networkCanvas = document.getElementById('network-canvas');
        this.coolantCanvas = document.getElementById('coolant-canvas');
        this.numberStreams = [
            document.getElementById('stream-1'),
            document.getElementById('stream-2'),
            document.getElementById('stream-3')
        ];
        this.diagCells = document.querySelectorAll('.diag-cell');
        this.hexCells = document.querySelectorAll('.hex');

        this.init();
    }

    init() {
        this.startRacingNumbers();
        this.startWaveform();
        this.startNetworkGraph();
        this.startCoolantFlow();
        this.startDiagnosticGrid();
        this.startHexGrid();
        this.startShipStats();
        this.startSystemReadouts();
        this.startPowerNodes();
        this.startArchButtons();
    }

    // ==========================================
    // COOLANT FLOW (Engineering)
    // ==========================================
    startCoolantFlow() {
        if (!this.coolantCanvas) return;

        const ctx = this.coolantCanvas.getContext('2d');
        const width = this.coolantCanvas.width;
        const height = this.coolantCanvas.height;

        let offset = 0;

        const draw = () => {
            ctx.fillStyle = 'rgba(0, 30, 30, 0.3)';
            ctx.fillRect(0, 0, width, height);

            // Draw flowing coolant
            ctx.strokeStyle = '#00ffcc';
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';

            for (let i = 0; i < 3; i++) {
                ctx.beginPath();
                ctx.globalAlpha = 0.3 + (i * 0.2);

                for (let x = 0; x < width; x += 2) {
                    const y = height / 2 +
                        Math.sin((x + offset + i * 20) * 0.05) * 15 +
                        Math.sin((x + offset) * 0.02) * 5;

                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }

                ctx.stroke();
            }

            ctx.globalAlpha = 1;

            // Flowing particles
            ctx.fillStyle = '#00ffcc';
            for (let i = 0; i < 8; i++) {
                const px = ((offset * 2 + i * 30) % (width + 20)) - 10;
                const py = height / 2 + Math.sin((px + offset) * 0.05) * 15;
                ctx.globalAlpha = 0.8;
                ctx.beginPath();
                ctx.arc(px, py, 2, 0, Math.PI * 2);
                ctx.fill();
            }

            ctx.globalAlpha = 1;
            offset += 2;
            requestAnimationFrame(draw);
        };

        draw();
    }

    // ==========================================
    // POWER NODES (Engineering)
    // ==========================================
    startPowerNodes() {
        const nodes = document.querySelectorAll('.power-node');
        if (!nodes.length) return;

        setInterval(() => {
            nodes.forEach(node => {
                if (Math.random() > 0.9 && !node.classList.contains('critical')) {
                    node.classList.toggle('active');
                }
            });
        }, 2000);
    }

    // ==========================================
    // ARCH BUTTONS (Holodeck)
    // ==========================================
    startArchButtons() {
        const buttons = document.querySelectorAll('.arch-button');
        const display = document.querySelector('.arch-display');
        const messages = ['READY', 'STANDBY', 'LOADING', 'ACTIVE', 'PAUSE'];

        if (!buttons.length) return;

        buttons.forEach((btn, i) => {
            btn.addEventListener('click', () => {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                if (display) {
                    display.textContent = messages[i] || 'READY';
                }

                if (window.soundSystem) {
                    window.soundSystem.playChirp();
                }
            });
        });
    }

    // ==========================================
    // RACING NUMBERS
    // Streams of hex/numbers scrolling by
    // ==========================================
    startRacingNumbers() {
        const generateStream = (length = 100) => {
            let stream = '';
            const chars = '0123456789ABCDEF';
            const words = ['NULL', 'SYNC', 'ACK', 'EOF', 'DATA', 'PKT', 'CMD'];

            for (let i = 0; i < length; i++) {
                if (Math.random() < 0.1) {
                    stream += ' ' + words[Math.floor(Math.random() * words.length)] + ' ';
                } else if (Math.random() < 0.3) {
                    stream += ' ';
                } else {
                    stream += chars[Math.floor(Math.random() * chars.length)];
                }
            }
            return stream + stream; // Duplicate for seamless loop
        };

        this.numberStreams.forEach((stream, i) => {
            if (stream) {
                stream.textContent = generateStream(80 + i * 20);
            }
        });

        // Periodically refresh the streams
        setInterval(() => {
            const randomStream = this.numberStreams[Math.floor(Math.random() * this.numberStreams.length)];
            if (randomStream) {
                randomStream.textContent = generateStream(80);
            }
        }, 15000);
    }

    // ==========================================
    // WAVEFORM DISPLAY
    // Audio-style waveform visualization
    // ==========================================
    startWaveform() {
        if (!this.waveformCanvas) return;

        const ctx = this.waveformCanvas.getContext('2d');
        const width = this.waveformCanvas.width;
        const height = this.waveformCanvas.height;

        let phase = 0;
        const frequencies = [0.05, 0.03, 0.07];
        const amplitudes = [15, 10, 8];

        const draw = () => {
            ctx.fillStyle = 'rgba(10, 15, 25, 0.3)';
            ctx.fillRect(0, 0, width, height);

            // Draw multiple waveforms
            const colors = ['#99ccff', '#cc99ff', '#ff9933'];

            frequencies.forEach((freq, i) => {
                ctx.beginPath();
                ctx.strokeStyle = colors[i];
                ctx.lineWidth = 1.5;
                ctx.globalAlpha = 0.7 - (i * 0.2);

                for (let x = 0; x < width; x++) {
                    const y = height / 2 +
                        Math.sin(x * freq + phase + i) * amplitudes[i] +
                        Math.sin(x * freq * 2 + phase * 1.5) * (amplitudes[i] / 2);

                    if (x === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }

                ctx.stroke();
            });

            ctx.globalAlpha = 1;

            // Add some noise dots
            ctx.fillStyle = '#99ccff';
            for (let i = 0; i < 5; i++) {
                if (Math.random() > 0.7) {
                    ctx.fillRect(
                        Math.random() * width,
                        Math.random() * height,
                        1, 1
                    );
                }
            }

            phase += 0.05;
            requestAnimationFrame(draw);
        };

        draw();
    }

    // ==========================================
    // NETWORK GRAPH
    // Calm, breathing network visualization
    // ==========================================
    startNetworkGraph() {
        if (!this.networkCanvas) return;

        const ctx = this.networkCanvas.getContext('2d');
        const width = this.networkCanvas.width;
        const height = this.networkCanvas.height;

        let time = 0;

        const draw = () => {
            // Clear with slight fade for trails
            ctx.fillStyle = 'rgba(10, 15, 25, 0.1)';
            ctx.fillRect(0, 0, width, height);

            // Draw subtle grid lines
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
            ctx.lineWidth = 1;
            for (let y = 20; y < height; y += 20) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }

            // Gentle breathing waves - slow sine curves
            const drawWave = (color, fillColor, yOffset, amplitude, speed, phaseOffset) => {
                ctx.beginPath();
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.5;

                for (let x = 0; x <= width; x += 3) {
                    const y = height / 2 + yOffset +
                        Math.sin(x * 0.02 + time * speed + phaseOffset) * amplitude +
                        Math.sin(x * 0.01 + time * speed * 0.5) * (amplitude * 0.3);

                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();

                // Soft fill
                ctx.lineTo(width, height / 2 + yOffset);
                ctx.lineTo(0, height / 2 + yOffset);
                ctx.closePath();
                ctx.fillStyle = fillColor;
                ctx.fill();
            };

            // Inbound - soft green, breathing upward
            drawWave('#44ff88', 'rgba(68, 255, 136, 0.08)', -5, 15, 0.015, 0);

            // Outbound - soft purple, breathing downward
            drawWave('#cc99ff', 'rgba(204, 153, 255, 0.08)', 5, 12, 0.012, Math.PI);

            // Center line
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(0, height / 2);
            ctx.lineTo(width, height / 2);
            ctx.stroke();

            // Update display values with gentle drift
            const netIn = document.getElementById('net-in');
            const netOut = document.getElementById('net-out');
            if (netIn) netIn.textContent = (1.5 + Math.sin(time * 0.02) * 0.8).toFixed(1);
            if (netOut) netOut.textContent = (0.8 + Math.cos(time * 0.015) * 0.4).toFixed(1);

            time += 1;
            requestAnimationFrame(draw);
        };

        draw();
    }

    // ==========================================
    // DIAGNOSTIC GRID
    // Random blinking cells
    // ==========================================
    startDiagnosticGrid() {
        if (!this.diagCells.length) return;

        const toggleCells = () => {
            this.diagCells.forEach(cell => {
                if (Math.random() > 0.85) {
                    cell.classList.toggle('active');
                }
            });
        };

        setInterval(toggleCells, 500);
    }

    // ==========================================
    // HEX GRID
    // Slower, more ambient blinking
    // ==========================================
    startHexGrid() {
        if (!this.hexCells.length) return;

        const toggleHex = () => {
            const randomHex = this.hexCells[Math.floor(Math.random() * this.hexCells.length)];
            randomHex.classList.toggle('active');
        };

        setInterval(toggleHex, 800);
    }

    // ==========================================
    // SHIP STATS
    // Slowly fluctuating values
    // ==========================================
    startShipStats() {
        const warpEl = document.getElementById('warp-factor');
        const shieldEl = document.getElementById('shield-pct');
        const hullEl = document.getElementById('hull-pct');

        let warp = 0;
        let shields = 100;
        let hull = 100;

        const updateStats = () => {
            // Warp fluctuates more dramatically
            warp += (Math.random() - 0.5) * 0.3;
            warp = Math.max(0, Math.min(9.9, warp));

            // Shields slowly drift
            shields += (Math.random() - 0.48) * 2;
            shields = Math.max(85, Math.min(100, shields));

            // Hull stays pretty stable
            hull += (Math.random() - 0.49) * 0.5;
            hull = Math.max(95, Math.min(100, hull));

            if (warpEl) warpEl.textContent = warp.toFixed(1);
            if (shieldEl) shieldEl.textContent = Math.round(shields) + '%';
            if (hullEl) hullEl.textContent = Math.round(hull) + '%';
        };

        setInterval(updateStats, 2000);
    }

    // ==========================================
    // SYSTEM READOUTS
    // Memory, temp, etc.
    // ==========================================
    startSystemReadouts() {
        const tempEl = document.getElementById('core-temp');
        const memEl = document.getElementById('memory-use');

        let temp = 37.2;
        let mem = 8.2;

        const updateReadouts = () => {
            temp += (Math.random() - 0.5) * 0.5;
            temp = Math.max(35, Math.min(45, temp));

            mem += (Math.random() - 0.5) * 0.3;
            mem = Math.max(6, Math.min(14, mem));

            if (tempEl) tempEl.textContent = temp.toFixed(1) + '°C';
            if (memEl) memEl.textContent = mem.toFixed(1) + ' GB';

            // Update bar fills
            const tempBar = tempEl?.closest('.readout-item')?.querySelector('.bar-fill');
            const memBar = memEl?.closest('.readout-item')?.querySelector('.bar-fill');

            if (tempBar) tempBar.style.width = ((temp - 30) / 20 * 100) + '%';
            if (memBar) memBar.style.width = (mem / 16 * 100) + '%';
        };

        setInterval(updateReadouts, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.decorativeEngine = new DecorativeEngine();
});

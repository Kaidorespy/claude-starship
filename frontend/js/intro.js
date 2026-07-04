/**
 * SHIP INTRO / MAP SYSTEM
 * The sleek entry point to Claude Hub
 */

class ShipIntro {
    constructor() {
        this.overlay = null;
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.particleCount = 120;
        this.animationId = null;
        this.cursor = null;
        this.isVisible = true;

        this.init();
    }

    init() {
        this.overlay = document.getElementById('ship-intro-overlay');
        this.canvas = document.getElementById('intro-field');
        this.cursor = document.getElementById('intro-cursor');

        if (!this.overlay) {
            console.warn('Ship intro overlay not found');
            return;
        }

        if (this.canvas) {
            this.ctx = this.canvas.getContext('2d');
            this.resizeCanvas();
            this.initParticles();
            this.animate();
        }

        this.initCursor();
        this.initNavigation();
        this.initCrewLocations();
        this.initMapButton();

        // Check if user wants to skip intro (localStorage preference)
        const skipIntro = localStorage.getItem('claude-hub-skip-intro');
        if (skipIntro === 'true') {
            this.hide(true); // instant hide
        }

        console.log('Ship intro initialized');
    }

    // ==========================================
    // PARTICLE SYSTEM
    // ==========================================

    resizeCanvas() {
        if (!this.canvas) return;
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;

        window.addEventListener('resize', () => {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
        });
    }

    initParticles() {
        this.particles = [];
        this.time = 0;
        this.nebulae = [];

        // Layered starfield - far to near
        const layers = [
            { count: 150, speed: 0.1, sizeRange: [0.3, 0.8], opacity: 0.3 },
            { count: 100, speed: 0.2, sizeRange: [0.5, 1.2], opacity: 0.5 },
            { count: 50, speed: 0.4, sizeRange: [1, 2], opacity: 0.8 },
            { count: 20, speed: 0.6, sizeRange: [1.5, 2.5], opacity: 1 }
        ];

        layers.forEach((layer, layerIndex) => {
            for (let i = 0; i < layer.count; i++) {
                this.particles.push({
                    x: Math.random() * this.canvas.width,
                    y: Math.random() * this.canvas.height,
                    z: layerIndex, // depth layer
                    speed: layer.speed,
                    radius: layer.sizeRange[0] + Math.random() * (layer.sizeRange[1] - layer.sizeRange[0]),
                    baseOpacity: layer.opacity * (0.5 + Math.random() * 0.5),
                    twinklePhase: Math.random() * Math.PI * 2,
                    twinkleSpeed: 0.5 + Math.random() * 2,
                    hue: Math.random() < 0.15 ? (Math.random() < 0.5 ? 30 : 200) : 25 // some gold, some blue, mostly warm
                });
            }
        });

        // Soft nebula patches
        for (let i = 0; i < 4; i++) {
            this.nebulae.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: 150 + Math.random() * 200,
                hue: [25, 270, 200, 320][i], // warm, purple, blue, magenta
                phase: Math.random() * Math.PI * 2
            });
        }
    }

    createParticle() {
        // Legacy - keep for compatibility
        return {
            x: Math.random() * this.canvas.width,
            y: Math.random() * this.canvas.height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            radius: Math.random() * 1.5 + 0.5,
            opacity: Math.random() * 0.5 + 0.1
        };
    }

    updateParticle(p) {
        // Drift toward center (approaching the ship)
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height / 2;

        p.x += (cx - p.x) * 0.0001 * p.speed;
        p.y += (cy - p.y) * 0.0001 * p.speed;

        // Slight wander
        p.x += (Math.random() - 0.5) * 0.1;
        p.y += (Math.random() - 0.5) * 0.1;
    }

    drawParticle(p) {
        const twinkle = Math.sin(this.time * p.twinkleSpeed + p.twinklePhase) * 0.3 + 0.7;
        const opacity = p.baseOpacity * twinkle;
        const size = p.radius * twinkle;

        // Glow for brighter stars
        if (p.z >= 2) {
            const glowSize = size * 4;
            const glow = this.ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, glowSize);
            glow.addColorStop(0, `hsla(${p.hue}, 60%, 90%, ${opacity * 0.15})`);
            glow.addColorStop(1, 'transparent');
            this.ctx.fillStyle = glow;
            this.ctx.fillRect(p.x - glowSize, p.y - glowSize, glowSize * 2, glowSize * 2);
        }

        // Star core
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
        this.ctx.fillStyle = `hsla(${p.hue}, 60%, 90%, ${opacity})`;
        this.ctx.fill();
    }

    drawNebulae() {
        this.nebulae.forEach(n => {
            const breathe = Math.sin(this.time * 0.2 + n.phase) * 0.15 + 0.85;
            const gradient = this.ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.radius * breathe);
            gradient.addColorStop(0, `hsla(${n.hue}, 40%, 20%, 0.06)`);
            gradient.addColorStop(0.5, `hsla(${n.hue}, 30%, 15%, 0.03)`);
            gradient.addColorStop(1, 'transparent');
            this.ctx.fillStyle = gradient;
            this.ctx.fillRect(n.x - n.radius, n.y - n.radius, n.radius * 2, n.radius * 2);
        });
    }

    drawConnections() {
        // Only connect nearby bright stars (layer 2+)
        const brightStars = this.particles.filter(p => p.z >= 2);

        for (let i = 0; i < brightStars.length; i++) {
            for (let j = i + 1; j < brightStars.length; j++) {
                const dx = brightStars[i].x - brightStars[j].x;
                const dy = brightStars[i].y - brightStars[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 80) {
                    const opacity = (1 - dist / 80) * 0.08;
                    this.ctx.beginPath();
                    this.ctx.moveTo(brightStars[i].x, brightStars[i].y);
                    this.ctx.lineTo(brightStars[j].x, brightStars[j].y);
                    this.ctx.strokeStyle = `rgba(255, 180, 130, ${opacity})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        }
    }

    animate() {
        if (!this.isVisible || !this.ctx) return;

        this.time += 0.016;

        // Deep space fade
        this.ctx.fillStyle = 'rgba(5, 5, 10, 0.15)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Nebulae first (behind stars)
        this.drawNebulae();

        // Stars by layer (far to near)
        for (let layer = 0; layer < 4; layer++) {
            this.particles
                .filter(p => p.z === layer)
                .forEach(p => {
                    this.updateParticle(p);
                    this.drawParticle(p);
                });
        }

        this.drawConnections();

        // Warm glow from ship direction (center)
        const shipGlow = this.ctx.createRadialGradient(
            this.canvas.width / 2, this.canvas.height / 2, 0,
            this.canvas.width / 2, this.canvas.height / 2, 400
        );
        const pulse = Math.sin(this.time * 0.5) * 0.02 + 0.05;
        shipGlow.addColorStop(0, `rgba(255, 150, 100, ${pulse})`);
        shipGlow.addColorStop(0.5, `rgba(255, 120, 80, ${pulse * 0.3})`);
        shipGlow.addColorStop(1, 'transparent');
        this.ctx.fillStyle = shipGlow;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this.animationId = requestAnimationFrame(() => this.animate());
    }

    // ==========================================
    // CURSOR
    // ==========================================

    initCursor() {
        if (!this.cursor) return;

        document.addEventListener('mousemove', (e) => {
            if (!this.isVisible) return;
            this.cursor.style.left = e.clientX - 10 + 'px';
            this.cursor.style.top = e.clientY - 10 + 'px';
        });

        // Hover states for interactive elements
        const interactives = this.overlay.querySelectorAll('.ship-room[data-section], .enter-ship-btn, .intro-crew-member');
        interactives.forEach(el => {
            el.addEventListener('mouseenter', () => this.cursor.classList.add('hover'));
            el.addEventListener('mouseleave', () => this.cursor.classList.remove('hover'));
        });
    }

    // ==========================================
    // NAVIGATION
    // ==========================================

    initNavigation() {
        // Section nodes
        const nodes = this.overlay.querySelectorAll('.section-node');
        nodes.forEach(node => {
            node.addEventListener('click', () => {
                const section = node.dataset.section;
                this.navigateToSection(section);
            });
        });

        // Enter ship button (goes to default section - claude/bridge)
        const enterBtn = this.overlay.querySelector('.enter-ship-btn');
        if (enterBtn) {
            enterBtn.addEventListener('click', () => {
                this.hide();
            });
        }

        // Crew member clicks navigate to their location
        const crewMembers = this.overlay.querySelectorAll('.intro-crew-member');
        crewMembers.forEach(member => {
            member.addEventListener('click', () => {
                const section = member.dataset.section;
                if (section) {
                    this.navigateToSection(section);
                }
            });
        });
    }

    navigateToSection(section) {
        // Hide the intro
        this.hide();

        // Trigger navigation in the main app
        setTimeout(() => {
            const navBtn = document.querySelector(`.nav-btn[data-section="${section}"]`);
            if (navBtn) {
                navBtn.click();
            }
        }, 100);
    }

    // ==========================================
    // CREW LOCATIONS (live from API)
    // ==========================================

    initCrewLocations() {
        this.updateCrewLocations();
        // Poll every 5 seconds for near-realtime crew movement
        setInterval(() => this.updateCrewLocations(), 5000);
    }

    async updateCrewLocations() {
        try {
            const response = await fetch(`${CONFIG.API_URL}/crew/locations`);
            if (!response.ok) return;

            const data = await response.json();
            const locations = data.locations || data;

            // Update crew panel
            this.updateCrewPanel(locations);
            // Update node indicators
            this.updateNodeIndicators(locations);
        } catch (error) {
            // Silently fail - backend might not be running
            console.debug('Could not fetch crew locations:', error.message);
        }
    }

    updateCrewPanel(locations) {
        const crewMap = {
            'claude': { name: 'Lumen', color: '#ff9966' },
            'server': { name: 'Alex', color: '#00d4ff' },
            'personal': { name: 'DQ', color: '#d4a574' },
            'science': { name: 'Mira', color: '#7799ff' },
            'games': { name: 'Holodeck', color: '#ffcc00' }
        };

        Object.entries(locations).forEach(([crewId, locData]) => {
            const member = this.overlay.querySelector(`.intro-crew-member[data-crew="${crewId}"]`);
            if (member) {
                const locationEl = member.querySelector('.intro-crew-location');
                if (locationEl) {
                    // locData is an object with location_name, or might be a string
                    const locationName = typeof locData === 'string' ? locData : (locData.location_name || locData.location || 'Unknown');
                    locationEl.textContent = this.formatLocation(locationName);
                }
            }
        });
    }

    updateNodeIndicators(locations) {
        // Clear all dynamic crew dots
        this.overlay.querySelectorAll('.crew-dot-dynamic').forEach(dot => dot.remove());
        this.overlay.querySelectorAll('.section-node').forEach(node => {
            node.classList.remove('has-crew');
        });

        // Crew colors
        const crewColors = {
            'claude': '#f7a844',   // Lumen - yellow/gold
            'server': '#00d4ff',   // Alex - cyan
            'personal': '#d4a574', // DQ - tan
            'science': '#7799ff',  // Mira - blue
            'games': '#ffcc00',    // Holodeck - yellow
            'med': '#ff6699',      // Ryn - pink
            'rec': '#e87c8a'       // Bartender - rose
        };

        // Map crew locations to data-section values
        const sectionMap = {
            'bridge': 'claude',
            'claude': 'claude',
            'engineering': 'servers',
            'server': 'servers',
            'ready_room': 'personal',
            'ready room': 'personal',
            'personal': 'personal',
            'science': 'science',
            'science_lab': 'science',
            'holodeck': 'games',
            'games': 'games',
            'mess_hall': 'messhall',
            'mess hall': 'messhall',
            'messhall': 'messhall',
            'navigation': 'nav',
            'medbay': 'med',
            'med': 'med',
            'observatory': 'observatory',
            'rec': 'rec',
            'rec_room': 'rec',
            'captains_quarters': 'captains',
            'captains': 'captains',
            'quarters': 'captains'
        };

        // Track how many dots per room for stacking
        const roomDotCount = {};

        Object.entries(locations).forEach(([crewId, locData]) => {
            // Holodeck has no physical body — no dot
            if (crewId === 'games') return;

            const location = typeof locData === 'string' ? locData : (locData.location_name || locData.location || '');
            const normalizedLoc = location.toLowerCase().replace(/\s+/g, '_');
            const section = sectionMap[normalizedLoc] || sectionMap[location.toLowerCase()];

            if (section) {
                const node = this.overlay.querySelector(`.section-node[data-section="${section}"]`);
                if (node) {
                    node.classList.add('has-crew');

                    // Create a colored dot for this crew member
                    const dot = document.createElement('div');
                    dot.className = 'crew-dot crew-dot-dynamic';
                    const dotColor = crewColors[crewId] || '#888';
                    dot.style.background = dotColor;
                    dot.style.color = dotColor; // for glow effect via currentColor
                    dot.style.opacity = '1';
                    dot.title = crewId;
                    dot.dataset.crew = crewId;

                    // Stack dots if multiple crew in same room
                    const count = roomDotCount[section] || 0;
                    dot.style.right = (6 + count * 14) + 'px';
                    roomDotCount[section] = count + 1;

                    node.appendChild(dot);
                }
            }
        });
    }

    formatLocation(location) {
        return location.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    // ==========================================
    // MAP BUTTON
    // ==========================================

    initMapButton() {
        const mapBtn = document.getElementById('map-return-btn');
        if (mapBtn) {
            mapBtn.addEventListener('click', () => this.show());
        }
    }

    // ==========================================
    // SHOW / HIDE
    // ==========================================

    show() {
        if (!this.overlay) return;

        this.overlay.classList.remove('hidden', 'instant-hide');
        this.isVisible = true;

        // Restart animation
        if (this.ctx && !this.animationId) {
            this.animate();
        }

        // Hide main cursor, show intro cursor
        document.body.style.cursor = 'none';
    }

    hide(instant = false) {
        if (!this.overlay) return;

        if (instant) {
            this.overlay.classList.add('instant-hide');
        } else {
            this.overlay.classList.add('hidden');
        }

        this.isVisible = false;

        // Stop animation to save resources
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        // Restore cursor
        document.body.style.cursor = '';
    }

    // Toggle intro preference
    setSkipIntro(skip) {
        localStorage.setItem('claude-hub-skip-intro', skip ? 'true' : 'false');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.shipIntro = new ShipIntro();
});

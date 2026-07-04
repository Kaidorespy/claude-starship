/**
 * Away Pings Panel & Captain Status - Fixed Position
 * Escapes elements from the rotated ship container so they display upright
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'claude-hub-away-pings-position';
    let originalParent = null;

    // Fix captain status button - move to body so it's not rotated
    function initCaptainStatus() {
        const captainStatus = document.getElementById('captain-status');
        if (!captainStatus) {
            setTimeout(initCaptainStatus, 500);
            return;
        }

        const CAPTAIN_POS_KEY = 'claude-hub-captain-status-position';

        // Load saved position or default
        let pos = { x: window.innerWidth / 2 - 60, y: window.innerHeight - 160 };
        try {
            const saved = localStorage.getItem(CAPTAIN_POS_KEY);
            if (saved) {
                const p = JSON.parse(saved);
                pos.x = Math.min(Math.max(0, p.x), window.innerWidth - 100);
                pos.y = Math.min(Math.max(0, p.y), window.innerHeight - 50);
            }
        } catch (e) {}

        // Create fixed wrapper
        const wrapper = document.createElement('div');
        wrapper.id = 'captain-status-fixed-wrapper';
        wrapper.style.cssText = `
            position: fixed !important;
            left: ${pos.x}px !important;
            top: ${pos.y}px !important;
            z-index: 10001 !important;
            cursor: grab !important;
        `;

        const isAway = captainStatus.classList.contains('away');

        const btn = document.createElement('button');
        btn.style.cssText = `
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;
            padding: 12px 24px !important;
            background: rgba(20, 22, 30, 0.9) !important;
            border: 2px solid ${isAway ? 'rgba(251, 191, 36, 0.5)' : 'rgba(74, 222, 128, 0.5)'} !important;
            border-radius: 25px !important;
            cursor: pointer !important;
            backdrop-filter: blur(8px) !important;
            transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
        `;

        const indicator = document.createElement('span');
        indicator.style.cssText = `
            display: inline-block !important;
            width: 14px !important;
            height: 14px !important;
            border-radius: 50% !important;
            background: ${isAway ? '#fbbf24' : '#4ade80'} !important;
            box-shadow: 0 0 12px ${isAway ? 'rgba(251, 191, 36, 0.7)' : 'rgba(74, 222, 128, 0.7)'} !important;
        `;

        const label = document.createElement('span');
        label.style.cssText = `
            font-family: 'Okuda', 'Share Tech Mono', monospace !important;
            font-size: 14px !important;
            letter-spacing: 3px !important;
            color: ${isAway ? '#fbbf24' : '#4ade80'} !important;
        `;
        label.textContent = isAway ? 'AWAY' : 'ON DECK';

        btn.appendChild(indicator);
        btn.appendChild(label);
        wrapper.appendChild(btn);

        // Drag functionality
        let isDragging = false;
        let dragStarted = false;
        let startX, startY, wrapperX, wrapperY;

        wrapper.addEventListener('mousedown', (e) => {
            startX = e.clientX;
            startY = e.clientY;
            const rect = wrapper.getBoundingClientRect();
            wrapperX = rect.left;
            wrapperY = rect.top;
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        function onMouseMove(e) {
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            if (!dragStarted && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
                dragStarted = true;
                isDragging = true;
                wrapper.style.cursor = 'grabbing';
            }
            if (isDragging) {
                const newX = Math.min(Math.max(0, wrapperX + dx), window.innerWidth - wrapper.offsetWidth);
                const newY = Math.min(Math.max(0, wrapperY + dy), window.innerHeight - wrapper.offsetHeight);
                wrapper.style.left = newX + 'px';
                wrapper.style.top = newY + 'px';
            }
        }

        function onMouseUp() {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            if (isDragging) {
                const rect = wrapper.getBoundingClientRect();
                localStorage.setItem(CAPTAIN_POS_KEY, JSON.stringify({ x: rect.left, y: rect.top }));
            }
            wrapper.style.cursor = 'grab';
            // Only trigger click if wasn't dragging
            if (!dragStarted) {
                captainStatus.querySelector('.captain-toggle')?.click();
            }
            isDragging = false;
            dragStarted = false;
        }

        // Sync styling when status changes
        const observer = new MutationObserver(() => {
            const away = captainStatus.classList.contains('away');
            btn.style.borderColor = away ? 'rgba(251, 191, 36, 0.5)' : 'rgba(74, 222, 128, 0.5)';
            indicator.style.background = away ? '#fbbf24' : '#4ade80';
            indicator.style.boxShadow = `0 0 12px ${away ? 'rgba(251, 191, 36, 0.7)' : 'rgba(74, 222, 128, 0.7)'}`;
            label.style.color = away ? '#fbbf24' : '#4ade80';
            label.textContent = away ? 'AWAY' : 'ON DECK';
        });
        observer.observe(captainStatus, { attributes: true, attributeFilter: ['class'] });

        document.body.appendChild(wrapper);

        // Hide the original (it's rotated inside ship-container)
        captainStatus.style.setProperty('display', 'none', 'important');

        // Only show wrapper on ship map (intro screen)
        const introOverlay = document.getElementById('ship-intro-overlay');
        function updateVisibility() {
            const introVisible = introOverlay &&
                !introOverlay.classList.contains('hidden') &&
                !introOverlay.classList.contains('instant-hide');
            wrapper.style.display = introVisible ? 'block' : 'none';
        }

        // Watch for intro overlay changes
        if (introOverlay) {
            const visObserver = new MutationObserver(updateVisibility);
            visObserver.observe(introOverlay, { attributes: true, attributeFilter: ['class', 'style'] });
        }
        updateVisibility();

        console.log('[Captain Status] Created fixed wrapper');
    }

    function init() {
        const panel = document.getElementById('away-pings');
        if (!panel) {
            setTimeout(init, 500);
            return;
        }

        originalParent = panel.parentNode;

        let isDragging = false;
        let dragStarted = false;
        let startX, startY;
        let panelX, panelY;

        function setDefaultPosition() {
            panelX = window.innerWidth - 320;
            panelY = 80;
        }

        function applyPosition() {
            // Use setProperty with !important to override any CSS
            panel.style.setProperty('position', 'fixed', 'important');
            panel.style.setProperty('left', panelX + 'px', 'important');
            panel.style.setProperty('top', panelY + 'px', 'important');
            panel.style.setProperty('right', 'auto', 'important');
            panel.style.setProperty('bottom', 'auto', 'important');
            panel.style.setProperty('transform', 'none', 'important');
            panel.style.setProperty('z-index', '10001', 'important');
        }

        function moveToBody() {
            if (panel.parentNode !== document.body) {
                document.body.appendChild(panel);
                console.log('[Away Pings] Moved to body');
            }
        }

        function moveToOriginal() {
            if (originalParent && panel.parentNode !== originalParent) {
                originalParent.appendChild(panel);
                // Reset inline styles when hidden
                panel.style.position = '';
                panel.style.left = '';
                panel.style.top = '';
                panel.style.right = '';
                panel.style.bottom = '';
                panel.style.transform = '';
                panel.style.zIndex = '';
                console.log('[Away Pings] Moved back to ship-container');
            }
        }

        function initPosition() {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                try {
                    const pos = JSON.parse(saved);
                    panelX = Math.min(Math.max(0, pos.x), window.innerWidth - 100);
                    panelY = Math.min(Math.max(0, pos.y), window.innerHeight - 50);
                } catch (e) {
                    setDefaultPosition();
                }
            } else {
                setDefaultPosition();
            }

            moveToBody();
            applyPosition();
            console.log('[Away Pings] Initialized at', panelX, panelY);
        }

        function savePosition() {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({ x: panelX, y: panelY }));
        }

        // Mouse drag
        function onMouseDown(e) {
            if (!e.target.closest('.away-pings-header')) return;
            if (e.button !== 0) return;

            startX = e.clientX;
            startY = e.clientY;

            const rect = panel.getBoundingClientRect();
            panelX = rect.left;
            panelY = rect.top;

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            e.preventDefault();
        }

        function onMouseMove(e) {
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            if (!dragStarted && (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5)) {
                dragStarted = true;
                isDragging = true;
                panel.classList.add('dragging');
            }

            if (isDragging) {
                const newX = panelX + deltaX;
                const newY = panelY + deltaY;
                const maxX = window.innerWidth - panel.offsetWidth;
                const maxY = window.innerHeight - panel.offsetHeight;

                panel.style.left = Math.min(Math.max(0, newX), maxX) + 'px';
                panel.style.top = Math.min(Math.max(0, newY), maxY) + 'px';
            }
        }

        function onMouseUp() {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);

            if (isDragging) {
                isDragging = false;
                dragStarted = false;
                panel.classList.remove('dragging');

                const rect = panel.getBoundingClientRect();
                panelX = rect.left;
                panelY = rect.top;
                savePosition();
            }
            dragStarted = false;
        }

        // Touch drag
        function onTouchStart(e) {
            if (!e.target.closest('.away-pings-header')) return;
            if (e.touches.length !== 1) return;

            const touch = e.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;

            const rect = panel.getBoundingClientRect();
            panelX = rect.left;
            panelY = rect.top;
        }

        function onTouchMove(e) {
            if (e.touches.length !== 1) return;

            const touch = e.touches[0];
            const deltaX = touch.clientX - startX;
            const deltaY = touch.clientY - startY;

            if (!dragStarted && (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10)) {
                dragStarted = true;
                isDragging = true;
                panel.classList.add('dragging');
            }

            if (isDragging) {
                const newX = panelX + deltaX;
                const newY = panelY + deltaY;
                const maxX = window.innerWidth - panel.offsetWidth;
                const maxY = window.innerHeight - panel.offsetHeight;

                panel.style.left = Math.min(Math.max(0, newX), maxX) + 'px';
                panel.style.top = Math.min(Math.max(0, newY), maxY) + 'px';
                e.preventDefault();
            }
        }

        function onTouchEnd() {
            if (isDragging) {
                isDragging = false;
                dragStarted = false;
                panel.classList.remove('dragging');

                const rect = panel.getBoundingClientRect();
                panelX = rect.left;
                panelY = rect.top;
                savePosition();
            }
            dragStarted = false;
        }

        // Bind events
        panel.addEventListener('mousedown', onMouseDown);
        panel.addEventListener('touchstart', onTouchStart, { passive: true });
        panel.addEventListener('touchmove', onTouchMove, { passive: false });
        panel.addEventListener('touchend', onTouchEnd);

        // Move to body immediately and keep it there
        moveToBody();
        applyPosition();

        // Visibility logic - show only if: no 'hidden' class AND on intro screen
        const introOverlay = document.getElementById('ship-intro-overlay');

        function updateVisibility() {
            const hasHiddenClass = panel.classList.contains('hidden');
            const introVisible = introOverlay &&
                !introOverlay.classList.contains('hidden') &&
                !introOverlay.classList.contains('instant-hide');

            // Show only on ship map AND when not hidden
            const shouldShow = !hasHiddenClass && introVisible;
            console.log('[Away Pings] Visibility check:', { hasHiddenClass, introVisible, shouldShow });
            panel.style.setProperty('display', shouldShow ? 'block' : 'none', 'important');
        }

        // Watch for panel 'hidden' class changes
        const panelObserver = new MutationObserver(updateVisibility);
        panelObserver.observe(panel, { attributes: true, attributeFilter: ['class'] });

        // Watch for intro overlay changes
        if (introOverlay) {
            const introObserver = new MutationObserver(updateVisibility);
            introObserver.observe(introOverlay, { attributes: true, attributeFilter: ['class', 'style'] });
        }

        // Initial visibility check
        updateVisibility();

        console.log('[Away Pings] Drag handler attached');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initCaptainStatus();
            init();
        });
    } else {
        initCaptainStatus();
        init();
    }

})();

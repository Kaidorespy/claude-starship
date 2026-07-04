/**
 * Floating Comms Panel
 * Draggable, collapsible, persists position and state.
 * Click header to collapse/expand. Drag header to move.
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'claude-hub-comms-state';
    const panel = document.getElementById('floating-comms');
    const header = panel?.querySelector('.comms-header');

    if (!panel || !header) return;

    let isDragging = false;
    let startX, startY;
    let panelX, panelY;
    let isCollapsed = false;
    let dragStartTime = 0;

    // Load saved state
    function loadState() {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const state = JSON.parse(saved);
                // Validate position is still on screen
                const maxX = window.innerWidth - panel.offsetWidth;
                const maxY = window.innerHeight - 40; // At least header visible
                panelX = Math.min(Math.max(0, state.x), maxX);
                panelY = Math.min(Math.max(0, state.y), maxY);
                isCollapsed = state.collapsed || false;
            } catch (e) {
                setDefaultState();
            }
        } else {
            setDefaultState();
        }
        applyState();
    }

    function setDefaultState() {
        // Default: bottom left area, expanded
        panelX = 20;
        panelY = window.innerHeight - 300;
        isCollapsed = false;
    }

    function applyState() {
        panel.style.left = panelX + 'px';
        panel.style.top = panelY + 'px';
        panel.style.right = 'auto';
        panel.style.bottom = 'auto';
        panel.classList.toggle('collapsed', isCollapsed);
    }

    function saveState() {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
            x: panelX,
            y: panelY,
            collapsed: isCollapsed
        }));
    }

    // Mouse events for dragging
    function onMouseDown(e) {
        if (e.button !== 0) return; // Only left click

        isDragging = true;
        dragStartTime = Date.now();
        panel.classList.add('dragging');

        startX = e.clientX - panelX;
        startY = e.clientY - panelY;

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);

        e.preventDefault();
    }

    function onMouseMove(e) {
        if (!isDragging) return;

        panelX = e.clientX - startX;
        panelY = e.clientY - startY;

        // Keep on screen
        const maxX = window.innerWidth - panel.offsetWidth;
        const maxY = window.innerHeight - 40;
        panelX = Math.min(Math.max(0, panelX), maxX);
        panelY = Math.min(Math.max(0, panelY), maxY);

        applyState();
    }

    function onMouseUp(e) {
        if (!isDragging) return;

        const dragDuration = Date.now() - dragStartTime;
        const wasDrag = dragDuration > 150 ||
            Math.abs(e.clientX - (startX + panelX)) > 5 ||
            Math.abs(e.clientY - (startY + panelY)) > 5;

        isDragging = false;
        panel.classList.remove('dragging');

        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);

        // If it was a quick click (not a drag), toggle collapse
        if (!wasDrag) {
            isCollapsed = !isCollapsed;
        }

        applyState();
        saveState();
    }

    // Touch events for mobile
    function onTouchStart(e) {
        if (e.touches.length !== 1) return;

        isDragging = true;
        dragStartTime = Date.now();
        panel.classList.add('dragging');

        const touch = e.touches[0];
        startX = touch.clientX - panelX;
        startY = touch.clientY - panelY;

        e.preventDefault();
    }

    function onTouchMove(e) {
        if (!isDragging || e.touches.length !== 1) return;

        const touch = e.touches[0];
        panelX = touch.clientX - startX;
        panelY = touch.clientY - startY;

        // Keep on screen
        const maxX = window.innerWidth - panel.offsetWidth;
        const maxY = window.innerHeight - 40;
        panelX = Math.min(Math.max(0, panelX), maxX);
        panelY = Math.min(Math.max(0, panelY), maxY);

        applyState();
        e.preventDefault();
    }

    function onTouchEnd() {
        if (!isDragging) return;

        const dragDuration = Date.now() - dragStartTime;

        isDragging = false;
        panel.classList.remove('dragging');

        // Quick tap = toggle collapse
        if (dragDuration < 200) {
            isCollapsed = !isCollapsed;
        }

        applyState();
        saveState();
    }

    // Handle window resize
    function onResize() {
        const maxX = window.innerWidth - panel.offsetWidth;
        const maxY = window.innerHeight - 40;

        if (panelX > maxX) panelX = Math.max(0, maxX);
        if (panelY > maxY) panelY = Math.max(0, maxY);
        if (panelX < 0) panelX = 0;
        if (panelY < 0) panelY = 0;

        applyState();
        saveState();
    }

    // Double-click to reset position
    function onDoubleClick() {
        setDefaultState();
        applyState();
        saveState();
    }

    // Hide on certain screens where it doesn't make sense
    function checkVisibility() {
        const container = document.querySelector('.hub-container');
        const theme = container?.getAttribute('data-theme');
        const introOverlay = document.getElementById('ship-intro-overlay');
        const introVisible = introOverlay && introOverlay.style.display !== 'none' && !introOverlay.classList.contains('hidden');

        // Hide on lightsout (sleeping) or when intro is showing
        const hideOn = ['lightsout'];
        const shouldHide = hideOn.includes(theme) || introVisible;
        panel.style.display = shouldHide ? 'none' : 'block';
    }

    // Watch for theme changes
    const observer = new MutationObserver(checkVisibility);
    const container = document.querySelector('.hub-container');
    if (container) {
        observer.observe(container, { attributes: true, attributeFilter: ['data-theme'] });
    }

    // Also watch for intro overlay changes
    const introOverlay = document.getElementById('ship-intro-overlay');
    if (introOverlay) {
        const introObserver = new MutationObserver(checkVisibility);
        introObserver.observe(introOverlay, { attributes: true, attributeFilter: ['style', 'class'] });
    }

    checkVisibility();

    // Initialize
    header.addEventListener('mousedown', onMouseDown);
    header.addEventListener('touchstart', onTouchStart, { passive: false });
    header.addEventListener('touchmove', onTouchMove, { passive: false });
    header.addEventListener('touchend', onTouchEnd);
    header.addEventListener('dblclick', onDoubleClick);
    window.addEventListener('resize', onResize);

    // Load state after brief delay
    setTimeout(loadState, 100);
    window.addEventListener('load', () => {
        setTimeout(loadState, 200);
    });

})();

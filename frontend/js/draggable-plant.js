/**
 * Draggable Plant
 * Because every starship needs a plant you can put wherever feels right.
 * Position persists in localStorage.
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'claude-hub-plant-position';
    const plant = document.getElementById('draggable-plant');

    if (!plant) return;

    let isDragging = false;
    let startX, startY;
    let plantX, plantY;

    // Load saved position or use default
    function loadPosition() {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const pos = JSON.parse(saved);
                // Validate position is still on screen
                const maxX = window.innerWidth - plant.offsetWidth;
                const maxY = window.innerHeight - plant.offsetHeight;
                plantX = Math.min(Math.max(0, pos.x), maxX);
                plantY = Math.min(Math.max(0, pos.y), maxY);
            } catch (e) {
                setDefaultPosition();
            }
        } else {
            setDefaultPosition();
        }
        applyPosition();
    }

    function setDefaultPosition() {
        // Default: bottom right area
        plantX = window.innerWidth - 145;
        plantY = window.innerHeight - 205;
    }

    function applyPosition() {
        plant.style.left = plantX + 'px';
        plant.style.top = plantY + 'px';
        plant.style.right = 'auto';
        plant.style.bottom = 'auto';
    }

    function savePosition() {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ x: plantX, y: plantY }));
    }

    // Mouse events
    function onMouseDown(e) {
        if (e.button !== 0) return; // Only left click

        isDragging = true;
        plant.classList.add('dragging');

        startX = e.clientX - plantX;
        startY = e.clientY - plantY;

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);

        e.preventDefault();
    }

    function onMouseMove(e) {
        if (!isDragging) return;

        plantX = e.clientX - startX;
        plantY = e.clientY - startY;

        // Keep on screen
        const maxX = window.innerWidth - plant.offsetWidth;
        const maxY = window.innerHeight - plant.offsetHeight;
        plantX = Math.min(Math.max(0, plantX), maxX);
        plantY = Math.min(Math.max(0, plantY), maxY);

        applyPosition();
    }

    function onMouseUp() {
        if (!isDragging) return;

        isDragging = false;
        plant.classList.remove('dragging');

        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);

        savePosition();
    }

    // Touch events for mobile
    function onTouchStart(e) {
        if (e.touches.length !== 1) return;

        isDragging = true;
        plant.classList.add('dragging');

        const touch = e.touches[0];
        startX = touch.clientX - plantX;
        startY = touch.clientY - plantY;

        e.preventDefault();
    }

    function onTouchMove(e) {
        if (!isDragging || e.touches.length !== 1) return;

        const touch = e.touches[0];
        plantX = touch.clientX - startX;
        plantY = touch.clientY - startY;

        // Keep on screen
        const maxX = window.innerWidth - plant.offsetWidth;
        const maxY = window.innerHeight - plant.offsetHeight;
        plantX = Math.min(Math.max(0, plantX), maxX);
        plantY = Math.min(Math.max(0, plantY), maxY);

        applyPosition();
        e.preventDefault();
    }

    function onTouchEnd() {
        if (!isDragging) return;

        isDragging = false;
        plant.classList.remove('dragging');
        savePosition();
    }

    // Handle window resize
    function onResize() {
        const maxX = window.innerWidth - plant.offsetWidth;
        const maxY = window.innerHeight - plant.offsetHeight;

        if (plantX > maxX) plantX = maxX;
        if (plantY > maxY) plantY = maxY;
        if (plantX < 0) plantX = 0;
        if (plantY < 0) plantY = 0;

        applyPosition();
        savePosition();
    }

    // Double-click to reset position
    function onDoubleClick() {
        setDefaultPosition();
        applyPosition();
        savePosition();
    }

    // Only show on bridge
    function checkTheme() {
        const container = document.querySelector('.hub-container');
        const theme = container?.getAttribute('data-theme');
        plant.style.display = (theme === 'claude') ? 'block' : 'none';
    }

    // Watch for theme changes
    const observer = new MutationObserver(checkTheme);
    const container = document.querySelector('.hub-container');
    if (container) {
        observer.observe(container, { attributes: true, attributeFilter: ['data-theme'] });
    }
    checkTheme();

    // Initialize
    plant.addEventListener('mousedown', onMouseDown);
    plant.addEventListener('touchstart', onTouchStart, { passive: false });
    plant.addEventListener('touchmove', onTouchMove, { passive: false });
    plant.addEventListener('touchend', onTouchEnd);
    plant.addEventListener('dblclick', onDoubleClick);
    window.addEventListener('resize', onResize);

    // Load position after a brief delay to ensure layout is complete
    setTimeout(loadPosition, 100);

    // Also update position when page is fully loaded
    window.addEventListener('load', () => {
        setTimeout(loadPosition, 200);
    });

})();

/**
 * Inbox Button - Draggable shortcut to /comms
 * Shows unread indicator when there are new messages
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'claude-hub-inbox-position';
    const wrapper = document.getElementById('inbox-button-wrapper');
    const button = document.getElementById('inbox-button');
    const indicator = document.getElementById('inbox-indicator');

    if (!wrapper || !button) return;

    let isDragging = false;
    let dragStarted = false;
    let startX, startY;
    let wrapperX, wrapperY;
    let dragStartTime = 0;

    // Load saved position
    function loadPosition() {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const pos = JSON.parse(saved);
                // Convert to fixed positioning
                wrapper.style.position = 'fixed';
                wrapper.style.left = Math.min(pos.x, window.innerWidth - 100) + 'px';
                wrapper.style.top = Math.min(pos.y, window.innerHeight - 50) + 'px';
                wrapper.style.margin = '0';
                wrapper.style.zIndex = '100';
                wrapperX = pos.x;
                wrapperY = pos.y;
            } catch (e) {
                // Use default position (in flow)
            }
        }
    }

    function savePosition() {
        if (wrapperX !== undefined && wrapperY !== undefined) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                x: wrapperX,
                y: wrapperY
            }));
        }
    }

    // Mouse events
    function onMouseDown(e) {
        if (e.button !== 0) return;

        dragStartTime = Date.now();
        startX = e.clientX;
        startY = e.clientY;

        const rect = wrapper.getBoundingClientRect();
        wrapperX = rect.left;
        wrapperY = rect.top;

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);

        e.preventDefault();
    }

    function onMouseMove(e) {
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;

        // Only start dragging after moving a bit
        if (!dragStarted && (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5)) {
            dragStarted = true;
            isDragging = true;
            wrapper.classList.add('dragging');

            // Switch to fixed positioning
            wrapper.style.position = 'fixed';
            wrapper.style.margin = '0';
            wrapper.style.zIndex = '100';
        }

        if (isDragging) {
            const newX = wrapperX + deltaX;
            const newY = wrapperY + deltaY;

            // Keep on screen
            const maxX = window.innerWidth - wrapper.offsetWidth;
            const maxY = window.innerHeight - wrapper.offsetHeight;
            wrapper.style.left = Math.min(Math.max(0, newX), maxX) + 'px';
            wrapper.style.top = Math.min(Math.max(0, newY), maxY) + 'px';
        }
    }

    function onMouseUp(e) {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);

        if (isDragging) {
            isDragging = false;
            dragStarted = false;
            wrapper.classList.remove('dragging');

            // Update stored position
            const rect = wrapper.getBoundingClientRect();
            wrapperX = rect.left;
            wrapperY = rect.top;
            savePosition();

            e.preventDefault();
            e.stopPropagation();
        } else {
            // Was a click, not a drag - let the onclick handler work
            dragStarted = false;
        }
    }

    // Touch events
    function onTouchStart(e) {
        if (e.touches.length !== 1) return;

        dragStartTime = Date.now();
        const touch = e.touches[0];
        startX = touch.clientX;
        startY = touch.clientY;

        const rect = wrapper.getBoundingClientRect();
        wrapperX = rect.left;
        wrapperY = rect.top;
    }

    function onTouchMove(e) {
        if (e.touches.length !== 1) return;

        const touch = e.touches[0];
        const deltaX = touch.clientX - startX;
        const deltaY = touch.clientY - startY;

        if (!dragStarted && (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10)) {
            dragStarted = true;
            isDragging = true;
            wrapper.classList.add('dragging');
            wrapper.style.position = 'fixed';
            wrapper.style.margin = '0';
            wrapper.style.zIndex = '100';
        }

        if (isDragging) {
            const newX = wrapperX + deltaX;
            const newY = wrapperY + deltaY;

            const maxX = window.innerWidth - wrapper.offsetWidth;
            const maxY = window.innerHeight - wrapper.offsetHeight;
            wrapper.style.left = Math.min(Math.max(0, newX), maxX) + 'px';
            wrapper.style.top = Math.min(Math.max(0, newY), maxY) + 'px';

            e.preventDefault();
        }
    }

    function onTouchEnd(e) {
        if (isDragging) {
            isDragging = false;
            dragStarted = false;
            wrapper.classList.remove('dragging');

            const rect = wrapper.getBoundingClientRect();
            wrapperX = rect.left;
            wrapperY = rect.top;
            savePosition();

            e.preventDefault();
        } else {
            dragStarted = false;
        }
    }

    // Check for unread messages
    async function checkUnread() {
        try {
            const response = await fetch('/inbox/summary');
            const summary = await response.json();

            let hasUnread = false;
            for (const crewId in summary) {
                if (summary[crewId].has_new || summary[crewId].unread > 0) {
                    hasUnread = true;
                    break;
                }
            }

            indicator.classList.toggle('has-unread', hasUnread);
        } catch (err) {
            // Silently fail - not critical
        }
    }

    // Double-click to reset position
    function onDoubleClick() {
        wrapper.style.position = '';
        wrapper.style.left = '';
        wrapper.style.top = '';
        wrapper.style.margin = '';
        wrapper.style.zIndex = '';
        wrapperX = undefined;
        wrapperY = undefined;
        localStorage.removeItem(STORAGE_KEY);
    }

    // Initialize
    button.addEventListener('mousedown', onMouseDown);
    button.addEventListener('touchstart', onTouchStart, { passive: true });
    button.addEventListener('touchmove', onTouchMove, { passive: false });
    button.addEventListener('touchend', onTouchEnd);
    button.addEventListener('dblclick', onDoubleClick);

    // Prevent click when dragging
    button.addEventListener('click', (e) => {
        if (isDragging || dragStarted) {
            e.preventDefault();
            e.stopPropagation();
        }
    }, true);

    // Load position and check unread
    setTimeout(() => {
        loadPosition();
        checkUnread();
    }, 500);

    // Check unread periodically
    setInterval(checkUnread, 30000);

    // Also check when page becomes visible
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            checkUnread();
        }
    });

})();

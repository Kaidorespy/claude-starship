/**
 * SHORTCUTS - Dynamic Tool Launcher System
 * Allows users to create custom executable shortcuts in any section
 */

class ShortcutsManager {
    constructor() {
        this.shortcuts = [];
        this.editMode = false;
        this.draggedShortcut = null;
        this.dragOffset = { x: 0, y: 0 };
        this.contextMenu = null;
        this.currentEditId = null;

        // Floating add button state
        this.addBtn = null;
        this.addBtnDragging = false;
        this.addBtnPos = { x: 0, y: 0 };
        this.addBtnDragStart = { x: 0, y: 0 };
        this.addBtnDragTime = 0;

        this.init();
    }

    async init() {
        await this.loadShortcuts();
        this.createFloatingAddButton();
        this.createEditModeIndicator();
        this.render();
        this.setupEventListeners();
        this.setupModalListeners();
        console.log('[Shortcuts] Initialized with', this.shortcuts.length, 'shortcuts');
    }

    async loadShortcuts() {
        try {
            const response = await fetch('/shortcuts');
            const data = await response.json();
            this.shortcuts = data.shortcuts || [];
        } catch (err) {
            console.error('[Shortcuts] Failed to load:', err);
            this.shortcuts = [];
        }
    }

    createFloatingAddButton() {
        // Create a single floating add button
        if (document.getElementById('floating-add-shortcut')) return;

        const addBtn = document.createElement('button');
        addBtn.id = 'floating-add-shortcut';
        addBtn.className = 'add-shortcut-btn floating';
        addBtn.innerHTML = '+';
        addBtn.title = 'Add shortcut (drag to move)';
        document.body.appendChild(addBtn);
        this.addBtn = addBtn;

        // Load saved position
        this.loadAddBtnPosition();

        // Click handler (only if not dragging)
        addBtn.addEventListener('click', (e) => {
            const dragDuration = Date.now() - this.addBtnDragTime;
            if (dragDuration < 200 && !this.addBtnDragging) {
                e.stopPropagation();
                const currentSection = this.getCurrentSection();
                this.openEditor(null, currentSection);
            }
        });

        // Drag handlers
        addBtn.addEventListener('mousedown', (e) => this.startAddBtnDrag(e));
        addBtn.addEventListener('touchstart', (e) => this.startAddBtnDrag(e), { passive: false });

        // Watch for theme changes to hide on intro
        this.setupAddBtnVisibility();
    }

    loadAddBtnPosition() {
        const saved = localStorage.getItem('claude-hub-add-shortcut-pos');
        if (saved) {
            try {
                const pos = JSON.parse(saved);
                this.addBtnPos.x = Math.min(Math.max(0, pos.x), window.innerWidth - 50);
                this.addBtnPos.y = Math.min(Math.max(0, pos.y), window.innerHeight - 50);
            } catch (e) {
                this.setDefaultAddBtnPosition();
            }
        } else {
            this.setDefaultAddBtnPosition();
        }
        this.applyAddBtnPosition();
    }

    setDefaultAddBtnPosition() {
        this.addBtnPos.x = 20;
        this.addBtnPos.y = window.innerHeight - 80;
    }

    applyAddBtnPosition() {
        if (!this.addBtn) return;
        this.addBtn.style.left = this.addBtnPos.x + 'px';
        this.addBtn.style.top = this.addBtnPos.y + 'px';
    }

    saveAddBtnPosition() {
        localStorage.setItem('claude-hub-add-shortcut-pos', JSON.stringify(this.addBtnPos));
    }

    startAddBtnDrag(e) {
        if (e.button && e.button !== 0) return;

        this.addBtnDragging = true;
        this.addBtnDragTime = Date.now();
        this.addBtn.classList.add('dragging');

        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;

        this.addBtnDragStart.x = clientX - this.addBtnPos.x;
        this.addBtnDragStart.y = clientY - this.addBtnPos.y;

        const moveHandler = (e) => this.dragAddBtn(e);
        const upHandler = () => {
            this.addBtnDragging = false;
            this.addBtn.classList.remove('dragging');
            document.removeEventListener('mousemove', moveHandler);
            document.removeEventListener('mouseup', upHandler);
            document.removeEventListener('touchmove', moveHandler);
            document.removeEventListener('touchend', upHandler);
            this.saveAddBtnPosition();
        };

        document.addEventListener('mousemove', moveHandler);
        document.addEventListener('mouseup', upHandler);
        document.addEventListener('touchmove', moveHandler, { passive: false });
        document.addEventListener('touchend', upHandler);

        e.preventDefault();
    }

    dragAddBtn(e) {
        if (!this.addBtnDragging) return;

        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;

        this.addBtnPos.x = clientX - this.addBtnDragStart.x;
        this.addBtnPos.y = clientY - this.addBtnDragStart.y;

        // Keep on screen
        this.addBtnPos.x = Math.min(Math.max(0, this.addBtnPos.x), window.innerWidth - 50);
        this.addBtnPos.y = Math.min(Math.max(0, this.addBtnPos.y), window.innerHeight - 50);

        this.applyAddBtnPosition();
        e.preventDefault();
    }

    setupAddBtnVisibility() {
        const checkVisibility = () => {
            if (!this.addBtn) return;
            const introOverlay = document.getElementById('ship-intro-overlay');
            const introVisible = introOverlay && !introOverlay.classList.contains('hidden') && !introOverlay.classList.contains('instant-hide');
            this.addBtn.style.display = introVisible ? 'none' : 'flex';
        };

        // Watch for intro overlay changes
        const introOverlay = document.getElementById('ship-intro-overlay');
        if (introOverlay) {
            const observer = new MutationObserver(checkVisibility);
            observer.observe(introOverlay, { attributes: true, attributeFilter: ['style', 'class'] });
        }

        checkVisibility();
        // Also check on theme change
        const container = document.querySelector('.hub-container');
        if (container) {
            const observer = new MutationObserver(checkVisibility);
            observer.observe(container, { attributes: true, attributeFilter: ['data-theme'] });
        }
    }

    getCurrentSection() {
        const container = document.querySelector('.hub-container');
        return container?.getAttribute('data-theme') || 'claude';
    }

    createEditModeIndicator() {
        if (document.querySelector('.edit-mode-indicator')) return;

        const indicator = document.createElement('div');
        indicator.className = 'edit-mode-indicator';
        indicator.innerHTML = 'EDIT MODE - Drag shortcuts to reposition • Click to exit';
        indicator.addEventListener('click', () => this.toggleEditMode());
        document.body.appendChild(indicator);
    }

    render() {
        // Remove existing shortcut containers
        document.querySelectorAll('.shortcuts-container').forEach(el => el.remove());

        // Group shortcuts by section
        const bySection = {};
        this.shortcuts.forEach(shortcut => {
            if (!bySection[shortcut.section]) {
                bySection[shortcut.section] = [];
            }
            bySection[shortcut.section].push(shortcut);
        });

        // Render shortcuts for each section
        Object.entries(bySection).forEach(([section, shortcuts]) => {
            const sectionEl = document.querySelector(`[data-section="${section}"]`);
            if (!sectionEl) return;

            // Create shortcuts container
            const container = document.createElement('div');
            container.className = 'shortcuts-container';
            container.dataset.section = section;

            shortcuts.forEach(shortcut => {
                container.appendChild(this.createShortcutElement(shortcut));
            });

            sectionEl.appendChild(container);
        });
    }

    createShortcutElement(shortcut) {
        const btn = document.createElement('button');
        btn.className = `shortcut-btn shape-${shortcut.style?.shape || 'square'} color-${shortcut.style?.color || 'cyan'} size-${shortcut.style?.size || 'medium'}`;
        btn.dataset.shortcutId = shortcut.id;
        btn.dataset.description = shortcut.description || '';
        btn.style.left = `${shortcut.position?.x || 5}%`;
        btn.style.top = `${shortcut.position?.y || 5}%`;
        btn.innerHTML = shortcut.icon || '●';

        // Add label if needed
        if (shortcut.label) {
            const label = document.createElement('span');
            label.className = `shortcut-label label-${shortcut.showLabel || 'hover'}`;
            label.textContent = shortcut.label;
            btn.appendChild(label);
        }

        // Click to launch (or select in edit mode)
        btn.addEventListener('click', (e) => {
            if (this.editMode) {
                e.stopPropagation();
                this.openEditor(shortcut.id);
            } else {
                this.launchShortcut(shortcut.id);
            }
        });

        // Right-click for context menu
        btn.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.showContextMenu(e, shortcut);
        });

        // Drag functionality (only in edit mode)
        btn.addEventListener('mousedown', (e) => {
            if (this.editMode && e.button === 0) {
                e.preventDefault();
                this.startDrag(btn, e);
            }
        });

        return btn;
    }

    async launchShortcut(shortcutId) {
        const btn = document.querySelector(`[data-shortcut-id="${shortcutId}"]`);
        if (!btn) return;

        const originalHTML = btn.innerHTML;

        try {
            // Show loading state
            const label = btn.querySelector('.shortcut-label');
            if (label) label.style.display = 'none';
            btn.innerHTML = '...';

            const response = await fetch(`/shortcuts/${shortcutId}/launch`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                btn.innerHTML = '✓';
                setTimeout(() => {
                    btn.innerHTML = originalHTML;
                }, 1000);
            } else {
                btn.innerHTML = '✗';
                console.warn('[Shortcuts] Launch failed:', result.error);
                setTimeout(() => {
                    btn.innerHTML = originalHTML;
                }, 2000);
            }
        } catch (err) {
            btn.innerHTML = '✗';
            console.error('[Shortcuts] Launch error:', err);
            setTimeout(() => {
                btn.innerHTML = originalHTML;
            }, 2000);
        }
    }

    startDrag(element, event) {
        this.draggedShortcut = element;
        const rect = element.getBoundingClientRect();

        this.dragOffset.x = event.clientX - rect.left;
        this.dragOffset.y = event.clientY - rect.top;

        element.classList.add('dragging');

        document.addEventListener('mousemove', this.onDragMove);
        document.addEventListener('mouseup', this.onDragEnd);
    }

    onDragMove = (event) => {
        if (!this.draggedShortcut) return;

        const parent = this.draggedShortcut.closest('.shortcuts-container') ||
                       this.draggedShortcut.parentElement;
        const parentRect = parent.getBoundingClientRect();

        const x = event.clientX - parentRect.left - this.dragOffset.x;
        const y = event.clientY - parentRect.top - this.dragOffset.y;

        // Convert to percentage
        const xPercent = (x / parentRect.width) * 100;
        const yPercent = (y / parentRect.height) * 100;

        // Clamp to bounds
        const clampedX = Math.max(0, Math.min(90, xPercent));
        const clampedY = Math.max(0, Math.min(90, yPercent));

        this.draggedShortcut.style.left = `${clampedX}%`;
        this.draggedShortcut.style.top = `${clampedY}%`;
    }

    onDragEnd = () => {
        if (!this.draggedShortcut) return;

        this.draggedShortcut.classList.remove('dragging');

        // Save new position
        const shortcutId = this.draggedShortcut.dataset.shortcutId;
        const xPercent = parseFloat(this.draggedShortcut.style.left);
        const yPercent = parseFloat(this.draggedShortcut.style.top);

        this.updateShortcutPosition(shortcutId, xPercent, yPercent);

        this.draggedShortcut = null;

        document.removeEventListener('mousemove', this.onDragMove);
        document.removeEventListener('mouseup', this.onDragEnd);
    }

    async updateShortcutPosition(shortcutId, x, y) {
        try {
            const response = await fetch(`/shortcuts/${shortcutId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ position: { x, y } })
            });
            const result = await response.json();
            if (!result.success) {
                console.error('[Shortcuts] Position update failed:', result.error);
            }
        } catch (err) {
            console.error('[Shortcuts] Position update error:', err);
        }
    }

    toggleEditMode() {
        this.editMode = !this.editMode;
        document.body.classList.toggle('shortcuts-edit-mode', this.editMode);
        console.log('[Shortcuts] Edit mode:', this.editMode);
    }

    showContextMenu(event, shortcut) {
        this.hideContextMenu();

        const menu = document.createElement('div');
        menu.className = 'shortcut-context-menu';
        menu.innerHTML = `
            <button data-action="edit">Edit</button>
            <button data-action="launch">Launch</button>
            <button data-action="delete" class="danger">Delete</button>
        `;

        menu.style.left = `${event.clientX}px`;
        menu.style.top = `${event.clientY}px`;

        menu.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            if (action === 'edit') {
                this.openEditor(shortcut.id);
            } else if (action === 'launch') {
                this.launchShortcut(shortcut.id);
            } else if (action === 'delete') {
                this.deleteShortcut(shortcut.id);
            }
            this.hideContextMenu();
        });

        document.body.appendChild(menu);
        this.contextMenu = menu;

        // Close on click outside
        setTimeout(() => {
            document.addEventListener('click', this.hideContextMenu, { once: true });
        }, 0);
    }

    hideContextMenu = () => {
        if (this.contextMenu) {
            this.contextMenu.remove();
            this.contextMenu = null;
        }
    }

    // ==========================================
    // MODAL / EDITOR
    // ==========================================

    setupModalListeners() {
        const modal = document.getElementById('shortcut-modal');
        if (!modal) return;

        // Close button
        document.getElementById('shortcut-close')?.addEventListener('click', () => this.closeEditor());
        document.getElementById('shortcut-cancel')?.addEventListener('click', () => this.closeEditor());

        // Click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.closeEditor();
        });

        // Save button
        document.getElementById('shortcut-save')?.addEventListener('click', () => this.saveShortcut());

        // Delete button
        document.getElementById('shortcut-delete')?.addEventListener('click', () => {
            const id = document.getElementById('shortcut-id').value;
            if (id) this.deleteShortcut(id);
            this.closeEditor();
        });

        // Icon picker
        document.getElementById('shortcut-icon-picker')?.addEventListener('click', (e) => {
            if (e.target.classList.contains('icon-option')) {
                document.querySelectorAll('.icon-option').forEach(opt => opt.classList.remove('selected'));
                e.target.classList.add('selected');
            }
        });

        // ESC to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                this.closeEditor();
            }
        });
    }

    openEditor(shortcutId = null, section = null) {
        const modal = document.getElementById('shortcut-modal');
        if (!modal) return;

        const isEdit = !!shortcutId;
        this.currentEditId = shortcutId;

        // Update title
        document.getElementById('shortcut-modal-title').textContent = isEdit ? 'EDIT SHORTCUT' : 'ADD SHORTCUT';

        // Show/hide delete button
        document.getElementById('shortcut-delete').style.display = isEdit ? 'block' : 'none';

        if (isEdit) {
            // Load existing shortcut data
            const shortcut = this.shortcuts.find(s => s.id === shortcutId);
            if (shortcut) {
                document.getElementById('shortcut-id').value = shortcut.id;
                document.getElementById('shortcut-section').value = shortcut.section;
                document.getElementById('shortcut-label').value = shortcut.label || '';
                document.getElementById('shortcut-path').value = shortcut.path || '';
                document.getElementById('shortcut-desc').value = shortcut.description || '';
                document.getElementById('shortcut-shape').value = shortcut.style?.shape || 'square';
                document.getElementById('shortcut-color').value = shortcut.style?.color || 'cyan';
                document.getElementById('shortcut-size').value = shortcut.style?.size || 'medium';

                // Set icon
                document.querySelectorAll('.icon-option').forEach(opt => {
                    opt.classList.toggle('selected', opt.dataset.icon === shortcut.icon);
                });

                // Set label display
                const labelDisplay = shortcut.showLabel || 'hover';
                document.querySelector(`input[name="shortcut-label-display"][value="${labelDisplay}"]`).checked = true;
            }
        } else {
            // Clear form for new shortcut
            document.getElementById('shortcut-id').value = '';
            document.getElementById('shortcut-section').value = section || '';
            document.getElementById('shortcut-label').value = '';
            document.getElementById('shortcut-path').value = '';
            document.getElementById('shortcut-desc').value = '';
            document.getElementById('shortcut-shape').value = 'square';
            document.getElementById('shortcut-color').value = 'cyan';
            document.getElementById('shortcut-size').value = 'medium';

            // Reset icon
            document.querySelectorAll('.icon-option').forEach((opt, i) => {
                opt.classList.toggle('selected', i === 0);
            });

            // Reset label display
            document.querySelector('input[name="shortcut-label-display"][value="hover"]').checked = true;
        }

        modal.classList.add('active');
    }

    closeEditor() {
        const modal = document.getElementById('shortcut-modal');
        if (modal) modal.classList.remove('active');
        this.currentEditId = null;
    }

    async saveShortcut() {
        const id = document.getElementById('shortcut-id').value;
        const section = document.getElementById('shortcut-section').value;
        const label = document.getElementById('shortcut-label').value.trim();
        const path = document.getElementById('shortcut-path').value.trim();
        const description = document.getElementById('shortcut-desc').value.trim();
        const shape = document.getElementById('shortcut-shape').value;
        const color = document.getElementById('shortcut-color').value;
        const size = document.getElementById('shortcut-size').value;
        const icon = document.querySelector('.icon-option.selected')?.dataset.icon || '●';
        const showLabel = document.querySelector('input[name="shortcut-label-display"]:checked')?.value || 'hover';

        if (!path) {
            alert('Please enter an executable path');
            return;
        }

        if (!section) {
            alert('Section is required');
            return;
        }

        const shortcutData = {
            section,
            label,
            path,
            description,
            icon,
            showLabel,
            style: { shape, color, size }
        };

        try {
            let response;
            if (id) {
                // Update existing
                response = await fetch(`/shortcuts/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(shortcutData)
                });
            } else {
                // Create new
                response = await fetch('/shortcuts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(shortcutData)
                });
            }

            const result = await response.json();

            if (result.success || result.shortcut) {
                this.closeEditor();
                await this.loadShortcuts();
                this.render();
                console.log('[Shortcuts] Saved:', result.shortcut?.id || id);
            } else {
                alert('Failed to save: ' + (result.error || 'Unknown error'));
            }
        } catch (err) {
            console.error('[Shortcuts] Save error:', err);
            alert('Failed to save shortcut');
        }
    }

    async deleteShortcut(shortcutId) {
        if (!confirm('Delete this shortcut?')) return;

        try {
            const response = await fetch(`/shortcuts/${shortcutId}`, { method: 'DELETE' });
            const result = await response.json();

            if (result.success) {
                await this.loadShortcuts();
                this.render();
                console.log('[Shortcuts] Deleted:', shortcutId);
            } else {
                alert('Failed to delete: ' + (result.error || 'Unknown error'));
            }
        } catch (err) {
            console.error('[Shortcuts] Delete error:', err);
            alert('Failed to delete shortcut');
        }
    }

    setupEventListeners() {
        // Keyboard shortcut for edit mode (Ctrl+Shift+E)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'E') {
                e.preventDefault();
                this.toggleEditMode();
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.shortcutsManager = new ShortcutsManager();
});

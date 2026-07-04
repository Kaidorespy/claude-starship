/**
 * PROJECT BOARD
 * Collaborative project management for the Science Lab
 */

class ProjectBoard {
    constructor() {
        this.baseUrl = `${CONFIG.API_URL}`;
        this.projects = [];
        this.currentProject = null;

        // Who's using the board - can be changed
        this.currentUser = {
            id: 'casey',
            name: window.getCaptainName ? window.getCaptainName() : 'Captain'
        };

        this.init();
    }

    // Set current user (crew can call this)
    setUser(id, name) {
        this.currentUser = { id, name: name || id };
        console.log(`[ProjectBoard] Now acting as ${this.currentUser.name}`);
    }

    init() {
        this.initButtons();
        this.initModals();
        this.loadProjects();
        this.loadActivity();
    }

    // ========== BUTTON HANDLERS ==========
    initButtons() {
        const newBtn = document.getElementById('new-project-btn');
        const boardBtn = document.getElementById('view-board-btn');

        if (newBtn) {
            newBtn.addEventListener('click', () => this.openNewProjectModal());
        }
        if (boardBtn) {
            boardBtn.addEventListener('click', () => this.openBoardModal());
        }
    }

    // ========== MODAL HANDLING ==========
    initModals() {
        // New Project Modal
        this.initModal('new-project-modal', 'new-project-close', 'new-project-cancel');
        document.getElementById('new-project-create')?.addEventListener('click', () => this.createProject());

        // Project Board Modal
        this.initModal('project-board-modal', 'project-board-close');

        // Project Detail Modal
        this.initModal('project-detail-modal', 'project-detail-close');
        document.getElementById('detail-join')?.addEventListener('click', () => this.joinProject());
        document.getElementById('detail-comment-input')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.value.trim()) {
                this.addComment(e.target.value.trim());
                e.target.value = '';
            }
        });
    }

    initModal(modalId, closeId, cancelId = null) {
        const modal = document.getElementById(modalId);
        const closeBtn = document.getElementById(closeId);
        const cancelBtn = cancelId ? document.getElementById(cancelId) : null;

        if (closeBtn) {
            closeBtn.addEventListener('click', () => modal?.classList.remove('active'));
        }
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => modal?.classList.remove('active'));
        }
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.classList.remove('active');
            });
        }
    }

    openNewProjectModal() {
        document.getElementById('new-project-modal')?.classList.add('active');
        document.getElementById('project-name')?.focus();
    }

    openBoardModal() {
        document.getElementById('project-board-modal')?.classList.add('active');
        this.renderBoard();
    }

    openDetailModal(project) {
        this.currentProject = project;
        const modal = document.getElementById('project-detail-modal');

        document.getElementById('detail-project-name').textContent = project.name;
        document.getElementById('detail-description').textContent = project.description || 'No description';
        document.getElementById('detail-state').textContent = project.currentState || 'Not tracked';
        document.getElementById('detail-next').textContent = project.nextSteps || 'Not defined';
        document.getElementById('detail-status').textContent = project.status;
        document.getElementById('detail-priority').textContent = project.priority;
        document.getElementById('detail-created').textContent = this.formatDate(project.createdAt);

        // Contributors
        const contribEl = document.getElementById('detail-contributors');
        const contributors = project.contributors || [];
        contribEl.innerHTML = contributors.map(c => `
            <div class="contributor">
                <span class="contributor-name">${c.name}</span>
                <span class="contributor-role">${c.role}</span>
            </div>
        `).join('') || '<div class="empty">No contributors yet</div>';

        // Tags
        const tagsEl = document.getElementById('detail-tags');
        const tags = project.tags || [];
        tagsEl.innerHTML = tags.map(t => `<span class="tag">${t}</span>`).join('') || '<span class="empty">No tags</span>';

        // Comments
        const commentsEl = document.getElementById('detail-comments');
        const comments = project.comments || [];
        commentsEl.innerHTML = comments.map(c => `
            <div class="comment">
                <div class="comment-header">
                    <span class="comment-author">${c.author}</span>
                    <span class="comment-time">${this.formatTime(c.timestamp)}</span>
                </div>
                <div class="comment-text">${this.escapeHtml(c.text)}</div>
            </div>
        `).join('') || '<div class="empty">No comments yet</div>';

        // Activity
        const activityEl = document.getElementById('detail-activity');
        const updates = (project.updates || []).slice(-5).reverse();
        activityEl.innerHTML = updates.map(u => `
            <div class="activity-mini-item">
                <span class="activity-by">${u.by}</span>
                <span class="activity-action">${u.action}</span>
            </div>
        `).join('') || '<div class="empty">No activity</div>';

        modal?.classList.add('active');
    }

    // ========== API CALLS ==========
    async loadProjects() {
        try {
            const response = await fetch(`${this.baseUrl}/projects`);
            const data = await response.json();
            this.projects = data.projects || [];
            this.renderSidebarProjects();
        } catch (error) {
            console.error('[ProjectBoard] Error loading projects:', error);
        }
    }

    async loadActivity() {
        try {
            const response = await fetch(`${this.baseUrl}/projects/activity?limit=10`);
            const data = await response.json();
            this.renderActivity(data.activity || []);
        } catch (error) {
            console.error('[ProjectBoard] Error loading activity:', error);
        }
    }

    async createProject() {
        const name = document.getElementById('project-name')?.value.trim();
        const description = document.getElementById('project-desc')?.value.trim();
        const status = document.getElementById('project-status')?.value || 'planning';
        const priority = document.getElementById('project-priority')?.value || 'medium';
        const tagsRaw = document.getElementById('project-tags')?.value || '';
        const tags = tagsRaw.split(',').map(t => t.trim()).filter(t => t);

        if (!name) {
            if (window.ambientSystem) window.ambientSystem.showToast('Project needs a name');
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/projects`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    description,
                    status,
                    priority,
                    tags,
                    created_by: this.currentUser.id
                })
            });

            const data = await response.json();

            if (data.status === 'created') {
                document.getElementById('new-project-modal')?.classList.remove('active');
                this.clearNewProjectForm();
                await this.loadProjects();
                await this.loadActivity();
                if (window.ambientSystem) window.ambientSystem.showToast('Project created!');
            }
        } catch (error) {
            console.error('[ProjectBoard] Error creating project:', error);
        }
    }

    async joinProject() {
        if (!this.currentProject) return;

        try {
            const response = await fetch(`${this.baseUrl}/projects/${this.currentProject.id}/contributors`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contributor_id: this.currentUser.id,
                    contributor_name: this.currentUser.name,
                    role: 'contributor'
                })
            });

            const data = await response.json();

            if (data.status === 'added') {
                await this.loadProjects();
                // Refresh detail view
                const updated = this.projects.find(p => p.id === this.currentProject.id);
                if (updated) this.openDetailModal(updated);
                if (window.ambientSystem) window.ambientSystem.showToast('Joined project!');
            } else if (data.error) {
                if (window.ambientSystem) window.ambientSystem.showToast(data.error);
            }
        } catch (error) {
            console.error('[ProjectBoard] Error joining project:', error);
        }
    }

    async addComment(text) {
        if (!this.currentProject) return;

        try {
            const response = await fetch(`${this.baseUrl}/projects/${this.currentProject.id}/comments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    author: this.currentUser.name,
                    text: text
                })
            });

            const data = await response.json();

            if (data.status === 'added') {
                await this.loadProjects();
                const updated = this.projects.find(p => p.id === this.currentProject.id);
                if (updated) this.openDetailModal(updated);
            }
        } catch (error) {
            console.error('[ProjectBoard] Error adding comment:', error);
        }
    }

    // ========== RENDERING ==========
    renderSidebarProjects() {
        const container = document.getElementById('active-projects');
        if (!container) return;

        const active = this.projects.filter(p =>
            p.status === 'active' || (p.priority === 'high' && p.status !== 'complete')
        ).slice(0, 5);

        if (active.length === 0) {
            container.innerHTML = '<div class="project-item dim">No active projects</div>';
            return;
        }

        container.innerHTML = active.map(p => `
            <div class="project-item clickable" data-id="${p.id}">
                <span class="project-status-dot ${p.status}"></span>
                <span class="project-name">${p.name}</span>
                ${p.priority === 'high' ? '<span class="priority-badge">!</span>' : ''}
            </div>
        `).join('');

        container.querySelectorAll('.project-item.clickable').forEach(el => {
            el.addEventListener('click', () => {
                const id = parseInt(el.dataset.id);
                const project = this.projects.find(p => p.id === id);
                if (project) this.openDetailModal(project);
            });
        });

        // Update stats
        document.getElementById('stat-total').textContent = this.projects.length;
        document.getElementById('stat-active').textContent = this.projects.filter(p => p.status === 'active').length;
        document.getElementById('stat-priority').textContent = this.projects.filter(p => p.priority === 'high').length;
        document.getElementById('stat-mystery').textContent = this.projects.filter(p => p.status === 'mystery').length;
    }

    renderActivity(activity) {
        const container = document.getElementById('project-activity');
        if (!container) return;

        if (activity.length === 0) {
            container.innerHTML = '<div class="activity-item dim">No recent activity</div>';
            return;
        }

        container.innerHTML = activity.slice(0, 6).map(a => `
            <div class="activity-item">
                <span class="activity-project">${a.project_name}</span>
                <span class="activity-detail">${a.by} ${a.action}</span>
            </div>
        `).join('');
    }

    renderBoard() {
        const columns = {
            planning: document.getElementById('col-planning'),
            active: document.getElementById('col-active'),
            paused: document.getElementById('col-paused'),
            mystery: document.getElementById('col-mystery'),
            complete: document.getElementById('col-complete')
        };

        // Clear columns
        Object.values(columns).forEach(col => {
            if (col) col.innerHTML = '';
        });

        // Sort projects into columns
        this.projects.forEach(p => {
            const col = columns[p.status];
            if (col) {
                const card = document.createElement('div');
                card.className = `board-card priority-${p.priority}`;
                card.innerHTML = `
                    <div class="card-name">${p.name}</div>
                    <div class="card-meta">
                        ${p.contributors?.length || 0} contributors
                        ${p.tags?.length ? `· ${p.tags.slice(0, 2).join(', ')}` : ''}
                    </div>
                `;
                card.addEventListener('click', () => this.openDetailModal(p));
                col.appendChild(card);
            }
        });
    }

    // ========== HELPERS ==========
    clearNewProjectForm() {
        document.getElementById('project-name').value = '';
        document.getElementById('project-desc').value = '';
        document.getElementById('project-status').value = 'planning';
        document.getElementById('project-priority').value = 'medium';
        document.getElementById('project-tags').value = '';
    }

    formatDate(timestamp) {
        if (!timestamp) return '--';
        return new Date(timestamp).toLocaleDateString();
    }

    formatTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        const mins = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        return date.toLocaleDateString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.projectBoard = new ProjectBoard();
});

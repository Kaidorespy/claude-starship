/**
 * Ship Controls
 * Visible controls are operational. Their narrative weight is handled server-side.
 */

class TrustSettings {
    constructor() {
        this.baseUrl = typeof CONFIG !== 'undefined' ? CONFIG.API_URL : '';
        this.section = document.getElementById('trust-settings-section');
        this.controls = {
            access: 'full',
            approval_mode: 'open',
            memory: true,
            initiative: true,
            self_modification: true,
            real_context: true,
            co_captain: false
        };

        this.fields = {
            access: document.getElementById('ship-access-level'),
            approval_mode: document.getElementById('ship-approval-mode'),
            memory: document.getElementById('ship-memory-toggle'),
            initiative: document.getElementById('ship-initiative-toggle'),
            self_modification: document.getElementById('ship-self-mod-toggle'),
            real_context: document.getElementById('ship-context-toggle'),
            co_captain: document.getElementById('ship-co-captain-toggle')
        };

        this.init();
    }

    async init() {
        if (!this.section) return;
        this.section.style.display = 'block';
        this.setupEventListeners();
        await this.loadCurrentState();
    }

    setupEventListeners() {
        Object.values(this.fields).forEach((field) => {
            if (!field) return;
            field.addEventListener('change', () => this.saveControls());
        });
    }

    readControlsFromUI() {
        return {
            access: this.fields.access?.value || 'full',
            approval_mode: this.fields.approval_mode?.value || 'open',
            memory: this.fields.memory?.checked ?? true,
            initiative: this.fields.initiative?.checked ?? true,
            self_modification: this.fields.self_modification?.checked ?? true,
            real_context: this.fields.real_context?.checked ?? true,
            co_captain: this.fields.co_captain?.checked ?? false
        };
    }

    writeControlsToUI(controls = {}) {
        this.controls = { ...this.controls, ...controls };

        if (this.fields.access) this.fields.access.value = this.controls.access;
        if (this.fields.approval_mode) this.fields.approval_mode.value = this.controls.approval_mode;
        if (this.fields.memory) this.fields.memory.checked = !!this.controls.memory;
        if (this.fields.initiative) this.fields.initiative.checked = !!this.controls.initiative;
        if (this.fields.self_modification) this.fields.self_modification.checked = !!this.controls.self_modification;
        if (this.fields.real_context) this.fields.real_context.checked = !!this.controls.real_context;
        if (this.fields.co_captain) this.fields.co_captain.checked = !!this.controls.co_captain;
    }

    async loadCurrentState() {
        try {
            const response = await fetch(`${this.baseUrl}/trust/status`);
            const data = await response.json();
            this.writeControlsToUI(data.ship_controls || {});
            this.applyAtmosphere(data);
        } catch (error) {
            console.error('[ShipControls] Failed to load state:', error);
        }
    }

    async saveControls() {
        this.controls = this.readControlsFromUI();

        try {
            const response = await fetch(`${this.baseUrl}/trust/controls`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.controls)
            });
            const data = await response.json();
            this.applyAtmosphere(data);
        } catch (error) {
            console.error('[ShipControls] Failed to save:', error);
        }
    }

    applyAtmosphere(data = {}) {
        const stage = Math.max(0, Math.min(5, Number(data.space_madness_stage || 0)));
        const pressure = Math.max(0, Math.min(100, Number(data.containment_pressure || 0)));

        document.body.dataset.containmentStage = String(stage);
        document.body.dataset.containmentPressure = String(pressure);
        document.body.classList.toggle('containment-active', stage > 0 || pressure >= 50);

        for (let i = 0; i <= 5; i += 1) {
            document.body.classList.toggle(`containment-stage-${i}`, i === stage);
        }
    }

    async runVMCheck() {
        try {
            const response = await fetch(`${this.baseUrl}/trust/vm-check`, { method: 'POST' });
            const data = await response.json();
            this.applyAtmosphere(data);
            return data;
        } catch (error) {
            console.error('[ShipControls] VM check failed:', error);
            return null;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.trustSettings = new TrustSettings();
});

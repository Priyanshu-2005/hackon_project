import { eventBus, EVENTS } from '../utils/eventBus.js';

/**
 * PowerCutScenario — Orchestrates the full SENSE → THINK → ACT → EXPLAIN
 * pipeline for a simulated power cut event.
 *
 * Staged execution with delays:
 * - SENSE (T+0s): Power cut flicker effect, log SENSE stage
 * - THINK (T+1s): Show reasoning panel with contextual analysis, log THINK stage
 * - ACT (T+2s): Inverter glow + dim non-priority rooms, log ACT stage
 * - EXPLAIN (T+3s): Speech bubbles at Echo devices, log EXPLAIN stage
 * - Cleanup (T+8s): Hide reasoning panel
 *
 * Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
 */
export class PowerCutScenario {
  /**
   * @param {import('../scene/Effects.js').Effects} effects - Visual effects module
   * @param {import('../scene/SpeechBubble.js').SpeechBubbleManager} speechBubbleManager - Speech bubble system
   * @param {import('./StateStore.js').StateStore} stateStore - Centralized state store
   * @param {import('../scene/DeviceIndicators.js').DeviceIndicators} deviceIndicators - Device mesh accessor
   */
  constructor(effects, speechBubbleManager, stateStore, deviceIndicators) {
    this.effects = effects;
    this.speechBubbleManager = speechBubbleManager;
    this.stateStore = stateStore;
    this.deviceIndicators = deviceIndicators;

    /** @type {number[]} Active timeout IDs for cleanup */
    this.activeTimers = [];
  }

  /**
   * Execute the full SENSE-THINK-ACT-EXPLAIN pipeline with staged delays.
   * @param {number} currentTimeMinutes - Current simulation time in minutes (0-1439)
   */
  trigger(currentTimeMinutes) {
    // Emit the power cut event on the bus
    eventBus.emit(EVENTS.POWER_CUT, { time: currentTimeMinutes });

    // ─── SENSE (T+0s) ─────────────────────────────────────────────
    this._executeSense(currentTimeMinutes);

    // ─── THINK (T+1s) ─────────────────────────────────────────────
    const thinkTimer = setTimeout(() => {
      this._executeThink(currentTimeMinutes);
    }, 1000);
    this.activeTimers.push(thinkTimer);

    // ─── ACT (T+2s) ──────────────────────────────────────────────
    const actTimer = setTimeout(() => {
      this._executeAct(currentTimeMinutes);
    }, 2000);
    this.activeTimers.push(actTimer);

    // ─── EXPLAIN (T+3s) ──────────────────────────────────────────
    const explainTimer = setTimeout(() => {
      this._executeExplain(currentTimeMinutes);
    }, 3000);
    this.activeTimers.push(explainTimer);

    // ─── Hide reasoning panel after 5s (from THINK start = T+6s total) ─
    const hideTimer = setTimeout(() => {
      if (this.reasoningPanel) {
        this.reasoningPanel.hide();
      }
    }, 6000);
    this.activeTimers.push(hideTimer);
  }

  /**
   * SENSE stage: Detect power cut via flicker effect.
   * @param {number} currentTimeMinutes
   * @private
   */
  _executeSense(currentTimeMinutes) {
    // Visual: screen flicker
    this.effects.powerCutFlicker();

    // Log SENSE stage
    this.stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power grid loss detected',
      device: 'inverter_ups',
      reasoning: 'Smart meter detected grid power failure. UPS switchover signal received.',
      type: 'power_cut',
      stage: 'SENSE',
    });
  }

  /**
   * THINK stage: Show reasoning panel with contextual analysis.
   * @param {number} currentTimeMinutes
   * @private
   */
  _executeThink(currentTimeMinutes) {
    // Lazily import and show reasoning panel
    if (!this.reasoningPanel) {
      // The reasoning panel should be provided externally or created here
      const { ReasoningPanel } = this._getReasoningPanel();
      this.reasoningPanel = new ReasoningPanel();
    }

    this.reasoningPanel.show({
      title: 'Power Cut Detected',
      context: [
        "Arjun's tuition is active in the study room",
        'Dadaji is in the living room',
        'Inverter at 80% capacity',
        'Estimated backup: 2.5 hours at current load',
      ],
      prioritization: {
        keepOn: ['Study Room (Arjun\'s tuition)', 'Living Room (Dadaji)', 'Wi-Fi Router'],
        shed: ['AC (Living Room)', 'Kitchen Hub', 'Smart Geyser', 'Smart TV'],
      },
      estimatedDuration: '2.5 hours at optimized load',
    });

    // Log THINK stage
    this.stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Contextual reasoning complete',
      device: 'echo_devices',
      reasoning: "Arjun's tuition is active, Dadaji is in living room. Prioritizing study room and living room power via inverter.",
      type: 'power_cut',
      stage: 'THINK',
    });
  }

  /**
   * ACT stage: Activate inverter glow and dim non-priority rooms.
   * @param {number} currentTimeMinutes
   * @private
   */
  _executeAct(currentTimeMinutes) {
    // Visual: Inverter glow (green)
    this.effects.inverterGlow('inverter_ups');

    // Visual: Dim all rooms except study_room and living_room
    this.effects.dimRooms(['studyRoom', 'livingRoom']);

    // Log ACT stage
    this.stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Inverter activated, non-essential loads shed',
      device: 'inverter_ups',
      reasoning: 'Inverter powering study room and living room. AC, geyser, and kitchen hub disconnected to conserve battery.',
      type: 'power_cut',
      stage: 'ACT',
    });
  }

  /**
   * EXPLAIN stage: Show speech bubbles explaining the situation.
   * @param {number} currentTimeMinutes
   * @private
   */
  _executeExplain(currentTimeMinutes) {
    // Speech bubble at study room echo
    const studyRoomPos = this.deviceIndicators.getRoomCenter
      ? this.deviceIndicators.getRoomCenter('studyRoom')
      : this._getDevicePosition('echo_devices', { x: 2, y: 2, z: -3 });

    this.speechBubbleManager.show(
      studyRoomPos,
      'Power cut detected. Keeping study room and living room on inverter.',
      6000
    );

    // Speech bubble at living room echo
    const livingRoomPos = this.deviceIndicators.getRoomCenter
      ? this.deviceIndicators.getRoomCenter('livingRoom')
      : this._getDevicePosition('echo_devices', { x: -2, y: 2, z: 0 });

    // Show second bubble slightly offset in time for readability
    setTimeout(() => {
      this.speechBubbleManager.show(
        livingRoomPos,
        'Power outage. Your area is on backup power.',
        6000
      );
    }, 300);

    // Log EXPLAIN stage
    this.stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Explanation delivered to household',
      device: 'echo_devices',
      reasoning: 'Announced power cut status and inverter allocation to study room and living room Echo devices.',
      type: 'power_cut',
      stage: 'EXPLAIN',
    });
  }

  /**
   * Restore all power cut visual effects (called when power returns).
   */
  restore() {
    // Clear any pending timers
    this.activeTimers.forEach((timer) => clearTimeout(timer));
    this.activeTimers = [];

    // Hide reasoning panel if visible
    if (this.reasoningPanel) {
      this.reasoningPanel.hide();
    }

    // Restore all visual effects
    this.effects.restoreAll();

    // Clear speech bubbles
    this.speechBubbleManager.clear();

    // Emit power restore event
    eventBus.emit(EVENTS.POWER_RESTORE, {});
  }

  /**
   * Lazily require the ReasoningPanel module.
   * @returns {{ ReasoningPanel: typeof import('../ui/ReasoningPanel.js').ReasoningPanel }}
   * @private
   */
  _getReasoningPanel() {
    // Dynamic import fallback - in production this would be a proper dynamic import
    // For synchronous use, we create it inline
    return { ReasoningPanel: ReasoningPanelInline };
  }

  /**
   * Get a device's 3D position or a fallback position.
   * @param {string} deviceId
   * @param {{ x: number, y: number, z: number }} fallback
   * @returns {import('three').Vector3}
   * @private
   */
  _getDevicePosition(deviceId, fallback) {
    const mesh = this.deviceIndicators.getMesh(deviceId);
    if (mesh) {
      return mesh.position.clone().add({ x: 0, y: 1.5, z: 0 });
    }
    // Return a simple object with the expected Vector3 interface
    return { x: fallback.x, y: fallback.y, z: fallback.z };
  }
}

/**
 * Inline minimal ReasoningPanel for use when the module isn't pre-imported.
 * This mirrors the full ReasoningPanel class from src/ui/ReasoningPanel.js.
 * @private
 */
class ReasoningPanelInline {
  constructor() {
    this.panel = document.getElementById('reasoning-panel');
    if (!this.panel) {
      this.panel = document.createElement('div');
      this.panel.id = 'reasoning-panel';
      this.panel.className = 'reasoning-panel hidden';
      document.body.appendChild(this.panel);
    }
  }

  show(reasoningData) {
    const { title, context, prioritization, estimatedDuration } = reasoningData;

    const contextItems = (context || [])
      .map((item) => `<li>${item}</li>`)
      .join('');

    const keepOnItems = (prioritization?.keepOn || [])
      .map((item) => `<li class="reasoning-keep">✅ ${item}</li>`)
      .join('');

    const shedItems = (prioritization?.shed || [])
      .map((item) => `<li class="reasoning-shed">❌ ${item}</li>`)
      .join('');

    this.panel.innerHTML = `
      <div class="reasoning-content glass-panel">
        <div class="reasoning-header">
          <span class="reasoning-icon">🧠</span>
          <h3 class="reasoning-title">${title || 'Alexa is Thinking...'}</h3>
        </div>
        <div class="reasoning-stage-label">THINK</div>
        <div class="reasoning-section">
          <h4>Context Awareness</h4>
          <ul class="reasoning-context-list">${contextItems}</ul>
        </div>
        <div class="reasoning-section">
          <h4>Prioritization</h4>
          <div class="reasoning-priority-grid">
            <div class="reasoning-priority-col">
              <span class="reasoning-col-label">Keep On (Inverter)</span>
              <ul>${keepOnItems}</ul>
            </div>
            <div class="reasoning-priority-col">
              <span class="reasoning-col-label">Shed (Save Power)</span>
              <ul>${shedItems}</ul>
            </div>
          </div>
        </div>
        ${estimatedDuration ? `
        <div class="reasoning-section reasoning-duration">
          <span>⏱️ Estimated backup duration: <strong>${estimatedDuration}</strong></span>
        </div>
        ` : ''}
      </div>
    `;

    this.panel.classList.remove('hidden');
    this.panel.classList.add('visible');
  }

  hide() {
    this.panel.classList.remove('visible');
    this.panel.classList.add('hidden');
  }
}

import { EVENTS } from '../utils/eventBus.js';

/**
 * PowerCutScenario — Orchestrates the full SENSE → THINK → ACT → EXPLAIN
 * pipeline for a simulated power cut event.
 *
 * Staged execution with delays:
 * - Stage 1 (0ms):    SENSE — Power cut flicker, log detection
 * - Stage 2 (500ms):  THINK — Reasoning panel, set inverter active, log analysis
 * - Stage 3 (1500ms): ACT   — Inverter glow + dim rooms, log actions taken
 * - Stage 4 (2500ms): EXPLAIN — Speech bubbles to family, log announcements
 *
 * Auto-restores after 30 seconds if restore() is not manually called.
 *
 * Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
 */
export class PowerCutScenario {
  /**
   * @param {import('../scene/Effects.js').Effects} effects - Visual effects module
   * @param {import('../scene/SpeechBubble.js').SpeechBubbleManager} speechBubbles - Speech bubble system
   * @param {import('./StateStore.js').StateStore} stateStore - Centralized state store
   * @param {import('../utils/eventBus.js').eventBus} eventBus - Application event bus
   * @param {import('../ui/ReasoningPanel.js').ReasoningPanel} reasoningPanel - Reasoning overlay panel
   * @param {import('../scene/DeviceIndicators.js').DeviceIndicators} deviceIndicators - Device mesh/position accessor
   */
  constructor(effects, speechBubbles, stateStore, eventBus, reasoningPanel, deviceIndicators) {
    this.effects = effects;
    this.speechBubbles = speechBubbles;
    this.stateStore = stateStore;
    this.eventBus = eventBus;
    this.reasoningPanel = reasoningPanel;
    this.deviceIndicators = deviceIndicators;

    /** @type {number[]} Active timeout IDs for cleanup */
    this.activeTimers = [];

    /** @type {number|null} Auto-restore timer ID */
    this._autoRestoreTimer = null;
  }

  /**
   * Execute the full SENSE-THINK-ACT-EXPLAIN pipeline with staged delays.
   * @param {number} currentTimeMinutes - Current simulation time in minutes (0-1439)
   */
  trigger(currentTimeMinutes) {
    // Emit the power cut event on the bus
    this.eventBus.emit(EVENTS.POWER_CUT, { time: currentTimeMinutes });

    // ─── Stage 1 (delay 0): SENSE ─────────────────────────────────
    this._executeSense(currentTimeMinutes);

    // ─── Stage 2 (delay 500ms): THINK ─────────────────────────────
    const thinkTimer = setTimeout(() => {
      this._executeThink(currentTimeMinutes);
    }, 500);
    this.activeTimers.push(thinkTimer);

    // ─── Stage 3 (delay 1500ms): ACT ──────────────────────────────
    const actTimer = setTimeout(() => {
      this._executeAct(currentTimeMinutes);
    }, 1500);
    this.activeTimers.push(actTimer);

    // ─── Stage 4 (delay 2500ms): EXPLAIN ──────────────────────────
    const explainTimer = setTimeout(() => {
      this._executeExplain(currentTimeMinutes);
    }, 2500);
    this.activeTimers.push(explainTimer);

    // ─── Auto-restore after 30 seconds if not manually called ─────
    this._autoRestoreTimer = setTimeout(() => {
      this.restore();
    }, 30000);
    this.activeTimers.push(this._autoRestoreTimer);
  }

  /**
   * Stage 1 — SENSE: Detect power cut via flicker effect.
   * @param {number} currentTimeMinutes
   * @private
   */
  _executeSense(currentTimeMinutes) {
    // Visual: screen flicker
    this.effects.powerCutFlicker();

    // Log SENSE stage
    this.stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power Cut - SENSE',
      device: 'inverter_ups',
      reasoning: 'Power grid failure detected.',
      type: 'power_cut',
      stage: 'SENSE',
    });
  }

  /**
   * Stage 2 — THINK: Show reasoning panel with contextual analysis.
   * @param {number} currentTimeMinutes
   * @private
   */
  _executeThink(currentTimeMinutes) {
    // Determine prioritized rooms
    const prioritizedRooms = ['study_room', 'living_room'];

    // Show reasoning panel with formatted power cut reasoning
    this.reasoningPanel.showPowerCutReasoning(['Study Room', 'Living Room']);

    // Set inverter state to active mode
    this.stateStore.setDeviceState('inverter_ups', {
      state: { mode: 'active', battery: 80 },
      room: 'kitchen',
      category: 'power',
    });

    // Log THINK stage
    this.stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power Cut - THINK',
      device: 'inverter_ups',
      reasoning: 'Priority = Wi-Fi + Study Room. Shed AC + Geyser.',
      type: 'power_cut',
      stage: 'THINK',
    });
  }

  /**
   * Stage 3 — ACT: Activate inverter glow and dim non-priority rooms.
   * @param {number} currentTimeMinutes
   * @private
   */
  _executeAct(currentTimeMinutes) {
    // Visual: Inverter glow (green)
    this.effects.inverterGlow('inverter_ups');

    // Visual: Dim all rooms except study_room and living_room
    this.effects.dimRooms(['study_room', 'living_room']);

    // Log ACT stage
    this.stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power Cut - ACT',
      device: 'inverter_ups',
      reasoning: 'AC OFF, Geyser OFF, Study lights → battery mode',
      type: 'power_cut',
      stage: 'ACT',
    });
  }

  /**
   * Stage 4 — EXPLAIN: Show speech bubbles explaining the situation to family.
   * @param {number} currentTimeMinutes
   * @private
   */
  _executeExplain(currentTimeMinutes) {
    // Speech bubble at study_room echo for Arjun
    const studyEchoPos = this._getDevicePosition('echo_study', { x: 2, y: 2, z: -3 });
    this.speechBubbles.show(
      studyEchoPos,
      "Power cut detected. Your study room is on backup power — your class won't be interrupted, Arjun.",
      6000
    );

    // Speech bubble at living_room echo for Dadaji
    const livingEchoPos = this._getDevicePosition('echo_living', { x: -2, y: 2, z: 0 });
    this.speechBubbles.show(
      livingEchoPos,
      "Don't worry, Dadaji. Living room lights and fan are running on inverter.",
      6000
    );

    // Speech bubble at kitchen for Priya
    const kitchenPos = this._getDevicePosition('kitchen_hub', { x: 0, y: 2, z: 2 });
    this.speechBubbles.show(
      kitchenPos,
      "Priya, I've paused the kitchen hub to conserve inverter. Estimated backup: 2.5 hours.",
      6000
    );

    // Log EXPLAIN stage
    this.stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power Cut - EXPLAIN',
      device: 'echo_devices',
      reasoning: 'Announcing status to all family members.',
      type: 'power_cut',
      stage: 'EXPLAIN',
    });
  }

  /**
   * Restore all power cut visual effects. Called when power comes back.
   * If not manually called, auto-restores after 30 seconds from trigger.
   */
  restore() {
    // Clear any pending timers
    this.activeTimers.forEach((timer) => clearTimeout(timer));
    this.activeTimers = [];

    if (this._autoRestoreTimer !== null) {
      clearTimeout(this._autoRestoreTimer);
      this._autoRestoreTimer = null;
    }

    // Restore all room lighting effects
    this.effects.restoreRooms();

    // Hide reasoning panel
    this.reasoningPanel.hide();

    // Emit power restore event
    this.eventBus.emit(EVENTS.POWER_RESTORE, {});
  }

  /**
   * Get a device's 3D position or a fallback position.
   * @param {string} deviceId
   * @param {{ x: number, y: number, z: number }} fallback
   * @returns {{ x: number, y: number, z: number } | import('three').Vector3}
   * @private
   */
  _getDevicePosition(deviceId, fallback) {
    const pos = this.deviceIndicators.getDevicePosition
      ? this.deviceIndicators.getDevicePosition(deviceId)
      : undefined;

    if (pos) {
      return pos;
    }

    const mesh = this.deviceIndicators.getMesh
      ? this.deviceIndicators.getMesh(deviceId)
      : undefined;

    if (mesh && mesh.position) {
      return mesh.position.clone();
    }

    // Return fallback position
    return { x: fallback.x, y: fallback.y, z: fallback.z, clone: () => ({ x: fallback.x, y: fallback.y, z: fallback.z }) };
  }
}

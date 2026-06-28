/**
 * Alexa Thinks Ahead — 2D Interactive Demo
 * Entry point: bootstraps all modules, wires connections, and starts the app.
 *
 * Requirements: 3.3, 7.1, 8.2
 */

// ─── Scene Module (2D Floor Plan) ────────────────────────────────
import { FloorPlan2D } from './scene/FloorPlan2D.js';

// ─── Simulation Modules ──────────────────────────────────────────
import { SimulationEngine } from './simulation/SimulationEngine.js';
import { StateStore } from './simulation/StateStore.js';
import { EventScheduler } from './simulation/EventScheduler.js';
import { PROACTIVE_ACTIONS } from './simulation/ProactiveActions.js';
import { PowerCutScenario } from './simulation/PowerCutScenario.js';

// ─── Data Layer ──────────────────────────────────────────────────
import { DataLayer } from './data/DataLayer.js';

// ─── UI Modules ──────────────────────────────────────────────────
import { UIManager } from './ui/UIManager.js';
import { LearningPanel } from './ui/LearningPanel.js';
import { DeploymentPanel } from './ui/DeploymentPanel.js';
import { EventLog } from './ui/EventLog.js';
import { TrustGauges } from './ui/TrustGauges.js';
import { ReasoningPanel } from './ui/ReasoningPanel.js';

// ─── Utilities ───────────────────────────────────────────────────
import { eventBus, EVENTS } from './utils/eventBus.js';

// ═══════════════════════════════════════════════════════════════════
// Bootstrap
// ═══════════════════════════════════════════════════════════════════

// --- Core instances ---
const simulationEngine = new SimulationEngine();
const stateStore = new StateStore();
const dataLayer = new DataLayer();

// --- 2D Floor Plan setup ---
const floorPlan = new FloorPlan2D(document.getElementById('3d-container'));

// --- UI setup ---
const uiManager = new UIManager(stateStore, simulationEngine);
const learningPanel = new LearningPanel(uiManager, eventBus, dataLayer);
const deploymentPanel = new DeploymentPanel(uiManager, simulationEngine);
const eventLog = new EventLog(stateStore);
const trustGauges = new TrustGauges(stateStore);

// --- Event Scheduler ---
const eventScheduler = new EventScheduler(simulationEngine, stateStore);
eventScheduler.loadActions(PROACTIVE_ACTIONS);

// --- Reasoning Panel ---
const reasoningPanel = new ReasoningPanel();

// --- Power Cut Scenario ---
// FloorPlan2D exposes the same interface as Effects + SpeechBubbleManager + DeviceIndicators
const powerCutScenario = new PowerCutScenario(
  floorPlan,        // effects (has highlightDevice, powerCutFlicker, inverterGlow, dimRooms, restoreRooms)
  floorPlan,        // speechBubbles (has show → we adapt below)
  stateStore,
  eventBus,
  reasoningPanel,
  floorPlan          // deviceIndicators (has getDevicePosition, getMesh)
);

// Monkey-patch speechBubbles.show to use floorPlan.showSpeechBubble
// PowerCutScenario calls: this.speechBubbles.show(position, text, duration)
// FloorPlan2D expects: showSpeechBubble(deviceId, text, duration)
// We provide a compatibility adapter:
const originalTrigger = powerCutScenario.trigger.bind(powerCutScenario);
powerCutScenario._originalSpeechBubblesShow = powerCutScenario.speechBubbles.show;

// Override the _executeExplain to use device-based speech bubbles
const originalExplain = powerCutScenario._executeExplain.bind(powerCutScenario);
powerCutScenario._executeExplain = function (currentTimeMinutes) {
  // Speech bubble at study_room echo for Arjun
  floorPlan.showSpeechBubble(
    'echo_study',
    "Power cut detected. Your study room is on backup power — your class won't be interrupted, Arjun.",
    6000
  );

  // Speech bubble at living_room echo for Dadaji
  floorPlan.showSpeechBubble(
    'echo_living',
    "Don't worry, Dadaji. Living room lights and fan are running on inverter.",
    6000
  );

  // Speech bubble at kitchen for Priya
  floorPlan.showSpeechBubble(
    'kitchen_hub',
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
};

// Override _executeAct to use FloorPlan2D methods
const originalAct = powerCutScenario._executeAct.bind(powerCutScenario);
powerCutScenario._executeAct = function (currentTimeMinutes) {
  // Visual: Inverter glow (green)
  floorPlan.inverterGlow('inverter_ups');

  // Visual: Dim all rooms except study_room and living_room
  floorPlan.dimRooms(['study_room', 'living_room']);

  // Log ACT stage
  this.stateStore.addEventLogEntry({
    time: currentTimeMinutes,
    action: 'Power Cut - ACT',
    device: 'inverter_ups',
    reasoning: 'AC OFF, Geyser OFF, Study lights → battery mode',
    type: 'power_cut',
    stage: 'ACT',
  });
};

// Override restore to use FloorPlan2D
const originalRestore = powerCutScenario.restore.bind(powerCutScenario);
powerCutScenario.restore = function () {
  // Clear any pending timers
  this.activeTimers.forEach((timer) => clearTimeout(timer));
  this.activeTimers = [];

  if (this._autoRestoreTimer !== null) {
    clearTimeout(this._autoRestoreTimer);
    this._autoRestoreTimer = null;
  }

  // Restore all room lighting effects
  floorPlan.restoreAll();

  // Hide reasoning panel
  this.reasoningPanel.hide();

  // Emit power restore event
  this.eventBus.emit(EVENTS.POWER_RESTORE, {});
};

// ═══════════════════════════════════════════════════════════════════
// Wire Connections
// ═══════════════════════════════════════════════════════════════════

// 1. Simulation tick → Floor Plan updates
simulationEngine.onTick((timeMinutes) => {
  floorPlan.updateAvatars(timeMinutes);
  floorPlan.updateLighting(timeMinutes);
});

// 2. Proactive action events → FloorPlan highlight + speech bubbles
eventBus.on(EVENTS.PROACTIVE_ACTION, (payload) => {
  // Highlight the target device with a glow pulse
  floorPlan.highlightDevice(payload.targetDevice);

  // Show speech bubble with the action's announcement
  const announcement = payload.announcement;
  const text = announcement
    ? announcement.parent || announcement.elder || announcement.child || payload.name
    : payload.name;

  floorPlan.showSpeechBubble(payload.targetDevice, text, 5000);
});

// 2b. On Deploy: if a CSV produced proactive actions, replace the hardcoded
//     defaults so the simulation is driven by the uploaded household data.
eventBus.on(EVENTS.PHASE_CHANGE, (payload) => {
  if (
    payload &&
    payload.phase === 'deployment' &&
    Array.isArray(payload.proactiveActions) &&
    payload.proactiveActions.length > 0
  ) {
    eventScheduler.loadActions(payload.proactiveActions);
    console.log(
      `Loaded ${payload.proactiveActions.length} CSV-derived proactive actions into the scheduler.`
    );
  }
});

// 3. Data mode toggle button
const dataToggleContainer = document.getElementById('data-toggle');
if (dataToggleContainer) {
  dataToggleContainer.innerHTML = `
    <div class="data-toggle-inner">
      <span class="data-toggle-label">Data Mode:</span>
      <button id="data-mode-btn" class="btn-accent data-mode-btn">
        Mock
      </button>
    </div>
  `;

  const dataModeBtn = document.getElementById('data-mode-btn');
  dataModeBtn.addEventListener('click', () => {
    const newMode = dataLayer.mode === 'mock' ? 'real' : 'mock';
    dataLayer.setMode(newMode);
    dataModeBtn.textContent = newMode === 'mock' ? 'Mock' : 'Real';
    dataModeBtn.classList.toggle('data-mode-real', newMode === 'real');
  });
}

// Helper: resolve a device ID to its room for the real-mode power-cut animation.
// Uses known device-to-room mappings from DEVICE_PLACEMENTS in FloorPlan2D.
const DEVICE_ROOM_MAP = {
  living_room_ac: 'living_room',
  smart_tv: 'living_room',
  echo_living: 'living_room',
  kitchen_hub: 'kitchen',
  water_purifier: 'kitchen',
  security_camera: 'balcony',
  smart_lock: 'balcony',
  smart_geyser: 'bath',
  inverter_ups: 'kitchen',
  echo_study: 'study_room',
  echo_kids: 'kids_room',
};
function _getDevicePlacement(deviceId) {
  return DEVICE_ROOM_MAP[deviceId] || null;
}

// 4. Power Cut button — wire the button rendered inside the timeline panel
const powerCutBtn = document.getElementById('power-cut-btn');
if (powerCutBtn) {
  powerCutBtn.addEventListener('click', async () => {
    const currentTimeMinutes = simulationEngine.currentTimeMinutes;

    // In real mode: call the backend scenario endpoint and animate from the response
    if (dataLayer.mode === 'real') {
      try {
        const response = await dataLayer.apiProvider.runPowerCutScenario();

        // --- Stage 1: SENSE (flicker effect) ---
        floorPlan.powerCutFlicker();
        stateStore.addEventLogEntry({
          time: currentTimeMinutes,
          action: 'Power Cut - SENSE',
          device: 'inverter_ups',
          reasoning: 'Power grid failure detected (real backend).',
          type: 'power_cut',
          stage: 'SENSE',
        });

        // --- Stage 2: THINK (show reasoning/explanation) ---
        setTimeout(() => {
          // Render the explanation and reasoning chain in the ReasoningPanel
          const reasoningContent = `
            <h3>⚡ Power Cut — Alexa's Reasoning (Live)</h3>
            <div class="reasoning-steps">
              <p>💬 <strong>Explanation:</strong> ${response.explanation || 'Analyzing situation...'}</p>
              ${response.reasoning_chain ? `<p>🧠 <strong>Reasoning:</strong> ${response.reasoning_chain}</p>` : ''}
            </div>
          `;
          reasoningPanel.show(reasoningContent);

          stateStore.addEventLogEntry({
            time: currentTimeMinutes,
            action: 'Power Cut - THINK',
            device: 'inverter_ups',
            reasoning: response.explanation || 'Contextual reasoning from backend.',
            type: 'power_cut',
            stage: 'THINK',
          });
        }, 500);

        // --- Stage 3: ACT (map target_devices to FloorPlan2D effects) ---
        setTimeout(() => {
          const roomsToKeepLit = [];

          for (const action of response.actions) {
            // Log each action to the EventLog
            stateStore.addEventLogEntry({
              time: currentTimeMinutes,
              action: `Power Cut - ACT: ${action.strategy}`,
              device: (action.target_devices || []).join(', '),
              reasoning: action.reasoning || `Strategy: ${action.strategy}, Confidence: ${action.confidence}`,
              type: 'power_cut',
              stage: 'ACT',
            });

            // Map target_devices to visual effects
            for (const deviceId of action.target_devices || []) {
              if (deviceId === 'inverter_ups') {
                floorPlan.inverterGlow(deviceId);
              } else {
                floorPlan.highlightDevice(deviceId, 3000);
              }

              // Track rooms that should stay lit (devices with power priority)
              if (action.strategy === 'energy_optimization' || action.strategy === 'priority_power') {
                const placement = _getDevicePlacement(deviceId);
                if (placement && !roomsToKeepLit.includes(placement)) {
                  roomsToKeepLit.push(placement);
                }
              }
            }
          }

          // Dim rooms — keep priority rooms lit
          const defaultPriorityRooms = ['study_room', 'living_room'];
          floorPlan.dimRooms(roomsToKeepLit.length > 0 ? roomsToKeepLit : defaultPriorityRooms);
        }, 1500);

        // --- Stage 4: EXPLAIN (speech bubbles with family-facing lines) ---
        setTimeout(() => {
          // Show explanation text as speech bubble on echo devices
          if (response.explanation) {
            floorPlan.showSpeechBubble('echo_living', response.explanation, 7000);
          }

          // Surface family-facing lines for specific members
          floorPlan.showSpeechBubble(
            'echo_study',
            "Your class won't be interrupted, Arjun. Study room is on backup power.",
            6000
          );
          floorPlan.showSpeechBubble(
            'kitchen_hub',
            "Kitchen hub paused to conserve inverter. Estimated backup: 2.5 hours.",
            6000
          );

          stateStore.addEventLogEntry({
            time: currentTimeMinutes,
            action: 'Power Cut - EXPLAIN',
            device: 'echo_devices',
            reasoning: response.explanation || 'Announcing status to family.',
            type: 'power_cut',
            stage: 'EXPLAIN',
          });
        }, 2500);

        // Auto-restore after 30 seconds
        setTimeout(() => {
          floorPlan.restoreAll();
          reasoningPanel.hide();
        }, 30000);

      } catch (err) {
        console.error('Real power-cut scenario failed, falling back to scripted:', err);
        // Show error indication in event log
        stateStore.addEventLogEntry({
          time: currentTimeMinutes,
          action: 'Power Cut - ERROR',
          device: 'system',
          reasoning: `Backend scenario failed: ${err.message}. Falling back to scripted demo.`,
          type: 'error',
          stage: 'ERROR',
        });
        // Fall back to scripted scenario
        powerCutScenario.trigger(currentTimeMinutes);
      }
    } else {
      // Mock mode: run existing scripted PowerCutScenario unchanged
      powerCutScenario.trigger(currentTimeMinutes);
    }
  });
}

// 5. Initialize trust gauges with mock data
dataLayer.getAutonomyTiers().then((tiersData) => {
  if (trustGauges.initializeFromData) {
    trustGauges.initializeFromData(tiersData);
  }
}).catch((err) => {
  console.warn('Failed to initialize trust gauges:', err);
});

// ═══════════════════════════════════════════════════════════════════
// Ready
// ═══════════════════════════════════════════════════════════════════
console.log('Alexa Thinks Ahead 2D Demo — all modules wired and ready.');

// Suppress unused variable warnings — these modules self-register via constructors
void learningPanel;
void deploymentPanel;
void eventLog;

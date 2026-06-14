/**
 * Alexa Thinks Ahead — 3D Interactive Demo
 * Entry point: bootstraps all modules, wires connections, and starts the app.
 *
 * Requirements: 3.3, 7.1, 8.2
 */

// ─── Scene Modules ───────────────────────────────────────────────
import * as THREE from 'three';
import { SceneManager } from './scene/SceneManager.js';
import { HouseBuilder } from './scene/HouseBuilder.js';
import { DeviceIndicators } from './scene/DeviceIndicators.js';
import { LightingSystem } from './scene/LightingSystem.js';
import { AvatarManager } from './scene/AvatarManager.js';
import { SpeechBubbleManager } from './scene/SpeechBubble.js';
import { Effects } from './scene/Effects.js';
import { ROOM_DEFINITIONS } from './scene/RoomDefinitions.js';

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

// ─── Utilities ───────────────────────────────────────────────────
import { eventBus, EVENTS } from './utils/eventBus.js';

// ═══════════════════════════════════════════════════════════════════
// Bootstrap
// ═══════════════════════════════════════════════════════════════════

// --- Core instances ---
const simulationEngine = new SimulationEngine();
const stateStore = new StateStore();
const dataLayer = new DataLayer();

// --- 3D Scene setup ---
const sceneManager = new SceneManager();
sceneManager.init(document.getElementById('3d-container'));

// Set scene background and lighting for visibility
sceneManager.scene.background = new THREE.Color(0x1a1a2e);

// Add hemisphere light for ambient fill (ensures house is always somewhat visible)
const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.3);
hemiLight.position.set(0, 20, 0);
sceneManager.scene.add(hemiLight);

const houseBuilder = new HouseBuilder(sceneManager.scene);
const houseGroup = houseBuilder.build();

const deviceIndicators = new DeviceIndicators(sceneManager.scene, ROOM_DEFINITIONS);
const lightingSystem = new LightingSystem(sceneManager.scene);
// Initialize lighting to daytime (noon) so the house is visible on load
lightingSystem.updateForTime(720);
const avatarManager = new AvatarManager(sceneManager.scene);
const speechBubbleManager = new SpeechBubbleManager(sceneManager.scene);
const effects = new Effects(sceneManager.scene, deviceIndicators);

// --- UI setup ---
const uiManager = new UIManager(stateStore, simulationEngine);
const learningPanel = new LearningPanel(uiManager);
const deploymentPanel = new DeploymentPanel(uiManager, simulationEngine);
const eventLog = new EventLog(stateStore);
const trustGauges = new TrustGauges(stateStore);

// --- Event Scheduler ---
const eventScheduler = new EventScheduler(simulationEngine, stateStore);
eventScheduler.loadActions(PROACTIVE_ACTIONS);

// --- Power Cut Scenario ---
const powerCutScenario = new PowerCutScenario(
  effects,
  speechBubbleManager,
  stateStore,
  deviceIndicators
);

// ═══════════════════════════════════════════════════════════════════
// Wire Connections
// ═══════════════════════════════════════════════════════════════════

// 1. Simulation tick → LightingSystem + AvatarManager
simulationEngine.onTick((timeMinutes) => {
  lightingSystem.updateForTime(timeMinutes);
  avatarManager.updatePositions(timeMinutes);
});

// 2. Proactive action events → Effects highlight + SpeechBubble announcements
eventBus.on(EVENTS.PROACTIVE_ACTION, (payload) => {
  // Highlight the target device with a glow pulse
  effects.highlightDevice(payload.targetDevice);

  // Show speech bubble with the action's announcement
  const announcement = payload.announcement;
  const text = announcement
    ? announcement.parent || announcement.elder || announcement.child || payload.name
    : payload.name;

  // Get device position for the speech bubble
  const position = deviceIndicators.getDevicePosition(payload.targetDevice);
  if (position) {
    position.y += 1.0; // Offset above the device
    speechBubbleManager.show(position, text, 5000);
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

// 4. Power Cut button — wired into the deployment phase
const timelinePanel = document.getElementById('timeline-panel');
if (timelinePanel) {
  const powerCutBtn = document.createElement('button');
  powerCutBtn.id = 'power-cut-btn';
  powerCutBtn.className = 'btn-accent power-cut-btn';
  powerCutBtn.textContent = '⚡ Power Cut';
  powerCutBtn.title = 'Simulate a power cut scenario';
  powerCutBtn.addEventListener('click', () => {
    powerCutScenario.trigger(simulationEngine.currentTimeMinutes);
  });
  timelinePanel.appendChild(powerCutBtn);
}

// 5. Initialize trust gauges with mock data
dataLayer.getAutonomyTiers().then((tiersData) => {
  trustGauges.initializeFromData(tiersData);
});

// ═══════════════════════════════════════════════════════════════════
// Ready
// ═══════════════════════════════════════════════════════════════════
console.log('Alexa Thinks Ahead 3D Demo — all modules wired and ready.');

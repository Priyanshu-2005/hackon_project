# Design Document

## Introduction

This document defines the architecture and technical design for the "Alexa Thinks Ahead" 3D Interactive Demo — a single-page web application built with Vite, Vanilla JS, and Three.js. The application renders an isometric low-poly 3D smart home with a two-phase wizard flow (Learning → Deployment), a simulation engine driving a 24-hour timeline, and visual effects demonstrating Alexa's proactive intelligence.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        index.html                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    main.js (entry)                        │    │
│  │  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐   │    │
│  │  │ Scene    │  │ Simulation   │  │ UI Manager      │   │    │
│  │  │ Manager  │  │ Engine       │  │                 │   │    │
│  │  │          │  │              │  │ ┌─────────────┐ │   │    │
│  │  │ ┌──────┐ │  │ ┌──────────┐│  │ │LearningPanel│ │   │    │
│  │  │ │House │ │  │ │Clock     ││  │ │DeployPanel  │ │   │    │
│  │  │ │Graph │ │  │ │EventQueue││  │ │EventLog     │ │   │    │
│  │  │ │Lights│ │  │ │SpeedCtrl ││  │ │Timeline     │ │   │    │
│  │  │ │Avatar│ │  │ │StateStore││  │ │TrustGauges  │ │   │    │
│  │  │ └──────┘ │  │ └──────────┘│  │ └─────────────┘ │   │    │
│  │  └──────────┘  └──────────────┘  └─────────────────┘   │    │
│  │        ▲               ▲                  ▲              │    │
│  │        └───────────────┼──────────────────┘              │    │
│  │                        │                                  │    │
│  │              ┌─────────────────┐                          │    │
│  │              │   Data Layer    │                          │    │
│  │              │ Mock ↔ Real API │                          │    │
│  │              └─────────────────┘                          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
alexa-thinks-ahead-3d-demo/
├── index.html
├── package.json
├── vite.config.js
├── public/
│   └── fonts/
├── src/
│   ├── main.js                  # Entry point, bootstraps app
│   ├── styles/
│   │   ├── main.css             # CSS custom properties, base styles
│   │   ├── glassmorphism.css    # Shared glassmorphism utilities
│   │   └── panels.css           # Panel-specific styles
│   ├── scene/
│   │   ├── SceneManager.js      # Three.js scene, camera, renderer, controls
│   │   ├── HouseBuilder.js      # Builds low-poly house geometry
│   │   ├── RoomDefinitions.js   # Room bounding boxes, positions, names
│   │   ├── DeviceIndicators.js  # Device mesh creation and placement
│   │   ├── AvatarManager.js     # Family avatar creation and movement
│   │   ├── LightingSystem.js    # Day/night cycle, ambient, directional lights
│   │   ├── SpeechBubble.js      # 3D speech bubble overlay
│   │   └── Effects.js           # Power cut flicker, glow, animations
│   ├── simulation/
│   │   ├── SimulationEngine.js  # Main clock, tick loop, event dispatch
│   │   ├── EventScheduler.js    # Time-based event queue evaluation
│   │   ├── StateStore.js        # Centralized device and family state
│   │   └── ProactiveActions.js  # Action definitions and trigger logic
│   ├── data/
│   │   ├── DataLayer.js         # Provider interface with mode toggle
│   │   ├── MockProvider.js      # Built-in mock data responses
│   │   ├── ApiProvider.js       # HTTP client for localhost:8080
│   │   └── schemas.js           # Shared response type definitions
│   ├── ui/
│   │   ├── UIManager.js         # Phase transitions, panel orchestration
│   │   ├── LearningPanel.js     # Event form, event list, deploy button
│   │   ├── DeploymentPanel.js   # Timeline, speed controls, presentation button
│   │   ├── EventLog.js          # Right sidebar event log entries
│   │   ├── TrustGauges.js       # Trust score gauge components
│   │   └── ReasoningPanel.js    # Power cut reasoning overlay
│   └── utils/
│       ├── constants.js         # Colors, sizes, timing constants
│       ├── eventBus.js          # Pub/sub event system
│       └── helpers.js           # Time formatting, interpolation utilities
```

## 3D Scene Architecture

### Scene Graph Hierarchy

```
Scene (Three.Scene)
├── AmbientLight
├── DirectionalLight (sun)
├── PointLight (accent, Alexa blue)
├── HouseGroup (Group)
│   ├── FloorMesh (BoxGeometry)
│   ├── WallsGroup
│   │   ├── ExteriorWalls (merged BufferGeometry)
│   │   └── InteriorWalls (merged BufferGeometry)
│   ├── RoomsGroup
│   │   ├── LivingRoom (Group) → furniture meshes
│   │   ├── MasterBedroom (Group)
│   │   ├── Kitchen (Group)
│   │   ├── Bath (Group)
│   │   ├── StudyRoom (Group)
│   │   ├── KidsRoom (Group)
│   │   └── Balcony (Group)
│   └── RoofGroup (cutaway geometry)
├── DevicesGroup (Group)
│   ├── DeviceIndicator × 10 (Mesh + label sprite)
├── AvatarsGroup (Group)
│   ├── FamilyAvatar × 6 (Mesh + name sprite)
└── OverlaysGroup (Group)
    └── SpeechBubble × N (CSS2DObject)
```

### Camera Setup

```javascript
// SceneManager.js
export class SceneManager {
  constructor(container) {
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
    // Isometric-like viewing angle
    this.camera.position.set(12, 10, 12);
    this.camera.lookAt(0, 0, 0);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.maxPolarAngle = Math.PI / 2.2;
    this.controls.minDistance = 5;
    this.controls.maxDistance = 30;
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
```

### Lighting System

```javascript
// LightingSystem.js
export class LightingSystem {
  constructor(scene) {
    this.scene = scene;
    this.ambient = new THREE.AmbientLight(0xffffff, 0.4);
    this.sun = new THREE.DirectionalLight(0xfff4e0, 0.8);
    this.sun.position.set(5, 10, 5);
    this.sun.castShadow = true;

    scene.add(this.ambient, this.sun);
  }

  /** @param {number} timeMinutes - 0 to 1439 */
  updateForTime(timeMinutes) {
    const { intensity, color } = this.calculateLighting(timeMinutes);
    this.ambient.intensity = intensity.ambient;
    this.ambient.color.set(color.ambient);
    this.sun.intensity = intensity.sun;
    this.sun.color.set(color.sun);
  }

  calculateLighting(timeMinutes) {
    const SUNRISE = 360;  // 06:00
    const SUNSET = 1080;  // 18:00
    const TRANSITION = 30; // 30-minute transition

    if (timeMinutes >= SUNRISE + TRANSITION && timeMinutes <= SUNSET - TRANSITION) {
      return { intensity: { ambient: 0.6, sun: 1.0 }, color: { ambient: 0xfff8f0, sun: 0xfff4e0 } };
    }
    if (timeMinutes < SUNRISE - TRANSITION || timeMinutes > SUNSET + TRANSITION) {
      return { intensity: { ambient: 0.15, sun: 0.05 }, color: { ambient: 0x4466aa, sun: 0x334488 } };
    }
    // Transition zones: interpolate
    let t;
    if (timeMinutes >= SUNRISE - TRANSITION && timeMinutes <= SUNRISE + TRANSITION) {
      t = (timeMinutes - (SUNRISE - TRANSITION)) / (TRANSITION * 2);
    } else {
      t = 1 - (timeMinutes - (SUNSET - TRANSITION)) / (TRANSITION * 2);
    }
    t = Math.max(0, Math.min(1, t));
    return this.interpolateLighting(t);
  }

  interpolateLighting(t) {
    // t=0 → night, t=1 → day
    const dayColor = new THREE.Color(0xfff8f0);
    const nightColor = new THREE.Color(0x4466aa);
    const ambientColor = nightColor.clone().lerp(dayColor, t);
    return {
      intensity: { ambient: 0.15 + 0.45 * t, sun: 0.05 + 0.95 * t },
      color: { ambient: ambientColor.getHex(), sun: 0xfff4e0 }
    };
  }
}
```

### Materials

```javascript
// constants.js
export const COLORS = {
  ACCENT: 0x00CAFF,        // Alexa blue
  DARK_BG: 0x0d1117,       // Dark base
  WALL: 0xf5e6d3,          // Warm wall tone
  FLOOR: 0xe8d5b7,         // Wooden floor
  ROOF: 0xcc7744,          // Terracotta roof
  DEVICE_GLOW: 0x00CAFF,   // Active device highlight
  AVATAR_COLORS: [0xff6b6b, 0x4ecdc4, 0x45b7d1, 0xf7dc6f, 0xbb8fce, 0x82e0aa],
};

export const MATERIALS = {
  wall: () => new THREE.MeshLambertMaterial({ color: COLORS.WALL }),
  floor: () => new THREE.MeshLambertMaterial({ color: COLORS.FLOOR }),
  device: () => new THREE.MeshPhongMaterial({ color: COLORS.ACCENT, emissive: COLORS.ACCENT, emissiveIntensity: 0.3 }),
  glass: () => new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.2, roughness: 0.1 }),
};
```

## State Management

### Simulation Clock

The simulation engine maintains a virtual clock that advances at a configurable multiplier relative to real time.

```javascript
// SimulationEngine.js
export class SimulationEngine {
  constructor() {
    this.currentTimeMinutes = 0;  // 0-1439 (00:00 to 23:59)
    this.speedMultiplier = 60;    // default 60x (1 sim-minute per real-second)
    this.isRunning = false;
    this.lastRealTime = null;
    this.listeners = new Set();
  }

  start() {
    this.isRunning = true;
    this.lastRealTime = performance.now();
    this.tick();
  }

  pause() { this.isRunning = false; }

  resume() {
    this.isRunning = true;
    this.lastRealTime = performance.now();
    this.tick();
  }

  setSpeed(multiplier) { this.speedMultiplier = multiplier; }

  seekTo(timeMinutes) {
    this.currentTimeMinutes = Math.max(0, Math.min(1439, timeMinutes));
    this.notifyListeners();
  }

  tick() {
    if (!this.isRunning) return;
    const now = performance.now();
    const realDeltaMs = now - this.lastRealTime;
    this.lastRealTime = now;

    // Convert real ms to simulated minutes
    const simDeltaMinutes = (realDeltaMs / 1000) * (this.speedMultiplier / 60);
    this.currentTimeMinutes += simDeltaMinutes;

    if (this.currentTimeMinutes >= 1440) {
      this.currentTimeMinutes = 1439;
      this.isRunning = false;
    }

    this.notifyListeners();
    if (this.isRunning) requestAnimationFrame(() => this.tick());
  }

  onTick(callback) { this.listeners.add(callback); }
  offTick(callback) { this.listeners.delete(callback); }
  notifyListeners() { this.listeners.forEach(cb => cb(this.currentTimeMinutes)); }
}
```

### Device State Store

```javascript
// StateStore.js
export class StateStore {
  constructor() {
    this.devices = new Map();      // deviceId → { state, room, category, tier }
    this.familyPositions = new Map(); // memberId → { room, activity }
    this.trustScores = new Map();  // category → { score, tier }
    this.events = [];              // Chronological event log entries
    this.listeners = new Map();    // key → Set<callback>
  }

  setDeviceState(deviceId, state) {
    this.devices.set(deviceId, { ...this.devices.get(deviceId), ...state });
    this.emit('device:' + deviceId, state);
  }

  setFamilyPosition(memberId, room, activity) {
    this.familyPositions.set(memberId, { room, activity });
    this.emit('family:' + memberId, { room, activity });
  }

  updateTrustScore(category, delta) {
    const current = this.trustScores.get(category) || { score: 0, tier: 1 };
    const newScore = Math.max(0, Math.min(100, current.score + delta));
    const tier = this.calculateTier(newScore);
    this.trustScores.set(category, { score: newScore, tier });
    this.emit('trust:' + category, { score: newScore, tier });
  }

  calculateTier(score) {
    if (score >= 91) return 5;
    if (score >= 71) return 4;
    if (score >= 46) return 3;
    if (score >= 21) return 2;
    return 1;
  }

  addEventLogEntry(entry) {
    this.events.push(entry);
    this.emit('eventlog', entry);
  }

  on(key, callback) {
    if (!this.listeners.has(key)) this.listeners.set(key, new Set());
    this.listeners.get(key).add(callback);
  }

  emit(key, data) {
    const cbs = this.listeners.get(key);
    if (cbs) cbs.forEach(cb => cb(data));
  }
}
```

### Family Schedule Data Structure

```javascript
// Family member positions change based on simulation time
export const FAMILY_SCHEDULE = {
  rajesh: [
    { start: 0, end: 420, room: 'masterBedroom', activity: 'sleeping' },
    { start: 420, end: 480, room: 'bath', activity: 'morning routine' },
    { start: 480, end: 540, room: 'kitchen', activity: 'breakfast' },
    { start: 540, end: 1080, room: null, activity: 'at work' },  // not visible
    { start: 1080, end: 1200, room: 'livingRoom', activity: 'relaxing' },
    { start: 1200, end: 1440, room: 'masterBedroom', activity: 'sleeping' },
  ],
  priya: [
    { start: 0, end: 390, room: 'masterBedroom', activity: 'sleeping' },
    { start: 390, end: 450, room: 'kitchen', activity: 'cooking' },
    { start: 450, end: 1020, room: null, activity: 'at work' },
    { start: 1020, end: 1140, room: 'kitchen', activity: 'dinner prep' },
    { start: 1140, end: 1440, room: 'livingRoom', activity: 'family time' },
  ],
  arjun: [
    { start: 0, end: 420, room: 'kidsRoom', activity: 'sleeping' },
    { start: 420, end: 480, room: 'kitchen', activity: 'breakfast' },
    { start: 480, end: 900, room: null, activity: 'at school' },
    { start: 900, end: 960, room: 'kitchen', activity: 'snack' },
    { start: 960, end: 1140, room: 'studyRoom', activity: 'tuition/study' },
    { start: 1140, end: 1440, room: 'kidsRoom', activity: 'relaxing' },
  ],
  ananya: [
    { start: 0, end: 420, room: 'kidsRoom', activity: 'sleeping' },
    { start: 420, end: 480, room: 'kitchen', activity: 'breakfast' },
    { start: 480, end: 960, room: null, activity: 'at school' },
    { start: 960, end: 1080, room: 'livingRoom', activity: 'activities' },
    { start: 1080, end: 1440, room: 'kidsRoom', activity: 'relaxing' },
  ],
  dadaji: [
    { start: 0, end: 360, room: 'masterBedroom', activity: 'sleeping' },
    { start: 360, end: 420, room: 'balcony', activity: 'morning walk' },
    { start: 420, end: 720, room: 'livingRoom', activity: 'reading/TV' },
    { start: 720, end: 900, room: 'masterBedroom', activity: 'rest' },
    { start: 900, end: 1260, room: 'livingRoom', activity: 'relaxing' },
    { start: 1260, end: 1440, room: 'masterBedroom', activity: 'sleeping' },
  ],
  dadiji: [
    { start: 0, end: 360, room: 'masterBedroom', activity: 'sleeping' },
    { start: 360, end: 480, room: 'kitchen', activity: 'tea/prayers' },
    { start: 480, end: 720, room: 'livingRoom', activity: 'watching TV' },
    { start: 720, end: 900, room: 'masterBedroom', activity: 'rest' },
    { start: 900, end: 1200, room: 'livingRoom', activity: 'family time' },
    { start: 1200, end: 1440, room: 'masterBedroom', activity: 'sleeping' },
  ],
};
```

## Data Layer Design

### Provider Interface

```javascript
// DataLayer.js
export class DataLayer {
  constructor() {
    this.mode = 'mock'; // 'mock' | 'real'
    this.mockProvider = new MockProvider();
    this.apiProvider = new ApiProvider('http://localhost:8080');
  }

  get provider() {
    return this.mode === 'mock' ? this.mockProvider : this.apiProvider;
  }

  setMode(mode) {
    this.mode = mode;
  }

  async getDevices() { return this.provider.getDevices(); }
  async getDeviceState(id) { return this.provider.getDeviceState(id); }
  async sendCommand(id, command) { return this.provider.sendCommand(id, command); }
  async getContextSnapshot() { return this.provider.getContextSnapshot(); }
  async getPatterns() { return this.provider.getPatterns(); }
  async getAutonomyTiers() { return this.provider.getAutonomyTiers(); }
  async updateTier(device, config) { return this.provider.updateTier(device, config); }
}
```

### Mock Provider

```javascript
// MockProvider.js
export class MockProvider {
  constructor() {
    this.devices = [
      { id: 'living_room_ac', name: 'Living Room AC', category: 'climate', room: 'livingRoom', brand: 'Daikin', state: { power: 'off', temperature: 24, mode: 'cool' } },
      { id: 'smart_lights', name: 'Smart Lights', category: 'lighting', room: 'all', brand: 'Philips Hue', state: { power: 'on', brightness: 80, colorTemp: 3000 } },
      { id: 'security_camera', name: 'Security Camera', category: 'security', room: 'balcony', brand: 'Ring', state: { power: 'on', recording: true, motionDetected: false } },
      { id: 'smart_lock', name: 'Smart Lock', category: 'security', room: 'balcony', brand: 'Yale', state: { locked: true, battery: 85 } },
      { id: 'kitchen_hub', name: 'Kitchen Appliance Hub', category: 'kitchen', room: 'kitchen', brand: 'Samsung', state: { power: 'on', activeAppliance: null } },
      { id: 'water_purifier', name: 'Water Purifier', category: 'utility', room: 'kitchen', brand: 'Kent', state: { power: 'on', filterLife: 72, waterLevel: 'full' } },
      { id: 'smart_geyser', name: 'Smart Geyser', category: 'utility', room: 'bath', brand: 'Havells', state: { power: 'off', temperature: 45, targetTemp: 55 } },
      { id: 'inverter_ups', name: 'Inverter/UPS', category: 'power', room: 'utility', brand: 'Luminous', state: { mode: 'standby', charge: 100, load: 0 } },
      { id: 'smart_tv', name: 'Smart TV', category: 'entertainment', room: 'livingRoom', brand: 'Fire TV', state: { power: 'off', input: 'hdmi1' } },
      { id: 'echo_devices', name: 'Echo Devices', category: 'assistant', room: 'livingRoom', brand: 'Amazon', state: { online: true, volume: 5 } },
    ];
  }

  async getDevices() {
    return { devices: this.devices, count: this.devices.length };
  }

  async getDeviceState(id) {
    const device = this.devices.find(d => d.id === id);
    return device ? { ...device } : null;
  }

  async sendCommand(id, command) {
    return { success: true, deviceId: id, command, timestamp: new Date().toISOString() };
  }

  async getContextSnapshot() {
    return {
      timestamp: new Date().toISOString(),
      deviceStates: this.devices.map(d => ({ id: d.id, state: d.state })),
      activeActivities: [],
      environmentals: { temperature: 34, humidity: 65, powerGrid: 'stable' },
    };
  }

  async getPatterns() {
    return {
      patterns: [
        { id: 'morning_routine', confidence: 0.92, schedule: '07:00', actions: ['geyser_preheat', 'lights_warm'] },
        { id: 'evening_cooling', confidence: 0.88, schedule: '17:30', actions: ['ac_precool'] },
        { id: 'security_away', confidence: 0.95, schedule: '09:00', actions: ['lock_arm', 'camera_alert'] },
      ],
    };
  }

  async getAutonomyTiers() {
    return {
      tiers: [
        { category: 'climate', currentTier: 3, trustScore: 55 },
        { category: 'lighting', currentTier: 4, trustScore: 78 },
        { category: 'security', currentTier: 2, trustScore: 35 },
        { category: 'kitchen', currentTier: 1, trustScore: 12 },
        { category: 'utility', currentTier: 3, trustScore: 62 },
        { category: 'power', currentTier: 3, trustScore: 50 },
        { category: 'entertainment', currentTier: 2, trustScore: 28 },
        { category: 'assistant', currentTier: 5, trustScore: 95 },
      ],
    };
  }

  async updateTier(device, config) {
    return { success: true, device, ...config };
  }
}
```

### API Provider

```javascript
// ApiProvider.js
export class ApiProvider {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async request(method, path, body = null) {
    const options = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) options.body = JSON.stringify(body);
    const response = await fetch(`${this.baseUrl}${path}`, options);
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  async getDevices() { return this.request('GET', '/api/v1/devices'); }
  async getDeviceState(id) { return this.request('GET', `/api/v1/devices/${id}/state`); }
  async sendCommand(id, command) { return this.request('POST', `/api/v1/devices/${id}/command`, command); }
  async getContextSnapshot() { return this.request('GET', '/api/v1/context/snapshot'); }
  async getPatterns() { return this.request('GET', '/api/v1/context/patterns'); }
  async getAutonomyTiers() { return this.request('GET', '/api/v1/autonomy/tiers'); }
  async updateTier(device, config) { return this.request('PUT', `/api/v1/autonomy/tiers/${device}`, config); }
}
```

## UI Component Design

### Phase Management (UIManager)

```javascript
// UIManager.js
export class UIManager {
  constructor(stateStore, simulationEngine) {
    this.currentPhase = 'learning'; // 'learning' | 'deployment'
    this.stateStore = stateStore;
    this.simulation = simulationEngine;
    this.panels = {};
  }

  init() {
    this.panels.learning = new LearningPanel(this);
    this.panels.deployment = new DeploymentPanel(this, this.simulation);
    this.panels.eventLog = new EventLog(this.stateStore);
    this.panels.trustGauges = new TrustGauges(this.stateStore);
    this.showPhase('learning');
  }

  deploy() {
    this.currentPhase = 'deployment';
    this.showPhase('deployment');
    this.simulation.start();
  }

  showPhase(phase) {
    document.getElementById('learning-phase').classList.toggle('hidden', phase !== 'learning');
    document.getElementById('deployment-phase').classList.toggle('hidden', phase !== 'deployment');
  }
}
```

### Learning Phase Panel

```javascript
// LearningPanel.js
export class LearningPanel {
  constructor(uiManager) {
    this.uiManager = uiManager;
    this.events = [...DEFAULT_EVENTS]; // Pre-populated family routines
    this.render();
    this.bindEvents();
  }

  addEvent(eventData) {
    this.events.push({ id: crypto.randomUUID(), ...eventData });
    this.renderEventList();
  }

  removeEvent(id) {
    this.events = this.events.filter(e => e.id !== id);
    this.renderEventList();
  }

  render() {
    const panel = document.getElementById('learning-panel');
    panel.innerHTML = `
      <div class="glass-panel">
        <h2>Configure Household Events</h2>
        <form id="event-form" class="event-form">
          <select name="eventType" required>
            <option value="">Event Type...</option>
            <option value="alarm">Morning Alarm</option>
            <option value="departure">Departure</option>
            <option value="arrival">Arrival</option>
            <option value="tuition">Tuition Class</option>
            <option value="dinner">Dinner Time</option>
            <option value="sleep">Sleep Time</option>
          </select>
          <input type="time" name="time" required />
          <select name="room" required>
            <option value="">Room...</option>
            <option value="livingRoom">Living Room</option>
            <option value="masterBedroom">Master Bedroom</option>
            <option value="kitchen">Kitchen</option>
            <option value="bath">Bath</option>
            <option value="studyRoom">Study Room</option>
            <option value="kidsRoom">Kids Room</option>
            <option value="balcony">Balcony</option>
          </select>
          <button type="submit" class="btn-accent">Add Event</button>
        </form>
        <div id="event-list" class="event-list"></div>
        <button id="deploy-btn" class="btn-deploy">Deploy →</button>
      </div>
    `;
  }
}
```

### Glassmorphism CSS

```css
/* glassmorphism.css */
:root {
  --color-accent: #00CAFF;
  --color-accent-rgb: 0, 202, 255;
  --color-bg-dark: #0d1117;
  --color-bg-panel: rgba(13, 17, 23, 0.7);
  --color-border: rgba(0, 202, 255, 0.15);
  --color-text: #e6edf3;
  --color-text-muted: #8b949e;
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --blur-amount: 12px;
  --border-radius: 12px;
}

body {
  margin: 0;
  background: var(--color-bg-dark);
  color: var(--color-text);
  font-family: var(--font-family);
  overflow: hidden;
}

.glass-panel {
  background: var(--color-bg-panel);
  backdrop-filter: blur(var(--blur-amount));
  -webkit-backdrop-filter: blur(var(--blur-amount));
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  padding: 1.5rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.btn-accent {
  background: linear-gradient(135deg, var(--color-accent), #0099cc);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.6rem 1.2rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.btn-accent:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(var(--color-accent-rgb), 0.4);
}

.btn-deploy {
  width: 100%;
  padding: 1rem;
  font-size: 1.1rem;
  margin-top: 1.5rem;
  background: linear-gradient(135deg, var(--color-accent), #0077aa);
  color: #fff;
  border: 2px solid var(--color-accent);
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
  letter-spacing: 0.5px;
}
```

### Timeline Scrubber

```javascript
// DeploymentPanel.js (timeline section)
export class DeploymentPanel {
  constructor(uiManager, simulation) {
    this.simulation = simulation;
    this.render();
    this.bindTimeline();
    this.bindSpeedControls();
  }

  bindTimeline() {
    const scrubber = document.getElementById('timeline-scrubber');
    scrubber.addEventListener('input', (e) => {
      this.simulation.seekTo(Number(e.target.value));
    });

    this.simulation.onTick((timeMinutes) => {
      scrubber.value = timeMinutes;
      document.getElementById('time-display').textContent = this.formatTime(timeMinutes);
    });
  }

  bindSpeedControls() {
    document.querySelectorAll('.speed-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const speed = Number(btn.dataset.speed);
        this.simulation.setSpeed(speed);
        document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  }

  formatTime(minutes) {
    const h = Math.floor(minutes / 60).toString().padStart(2, '0');
    const m = Math.floor(minutes % 60).toString().padStart(2, '0');
    return `${h}:${m}`;
  }
}
```

## Event System

### Pub/Sub Event Bus

```javascript
// eventBus.js
class EventBus {
  constructor() {
    this.handlers = new Map();
  }

  on(event, handler) {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event).add(handler);
    return () => this.off(event, handler);
  }

  off(event, handler) {
    const set = this.handlers.get(event);
    if (set) set.delete(handler);
  }

  emit(event, payload) {
    const set = this.handlers.get(event);
    if (set) set.forEach(handler => handler(payload));
  }
}

export const eventBus = new EventBus();

// Event types
export const EVENTS = {
  SIMULATION_TICK: 'simulation:tick',
  PHASE_CHANGE: 'phase:change',
  DEVICE_STATE_CHANGE: 'device:stateChange',
  PROACTIVE_ACTION: 'proactive:action',
  SPEECH_BUBBLE: 'speech:bubble',
  POWER_CUT: 'power:cut',
  POWER_RESTORE: 'power:restore',
  TRUST_UPDATE: 'trust:update',
  EVENT_ADDED: 'event:added',
  EVENT_REMOVED: 'event:removed',
};
```

### Proactive Action Scheduler

The simulation engine evaluates scheduled proactive actions against the current time and fires events when triggers are met.

```javascript
// EventScheduler.js
export class EventScheduler {
  constructor(simulationEngine, stateStore, eventBus) {
    this.simulation = simulationEngine;
    this.store = stateStore;
    this.bus = eventBus;
    this.scheduledActions = [];
    this.firedActions = new Set(); // Track already-fired one-time actions

    this.simulation.onTick((time) => this.evaluate(time));
  }

  loadActions(actions) {
    this.scheduledActions = actions.map(a => ({ ...a, id: crypto.randomUUID() }));
    this.firedActions.clear();
  }

  evaluate(currentTimeMinutes) {
    for (const action of this.scheduledActions) {
      if (this.firedActions.has(action.id)) continue;
      if (currentTimeMinutes >= action.triggerTime) {
        this.firedActions.add(action.id);
        this.bus.emit(EVENTS.PROACTIVE_ACTION, {
          ...action,
          timestamp: currentTimeMinutes,
        });
        this.store.addEventLogEntry({
          time: currentTimeMinutes,
          action: action.name,
          device: action.targetDevice,
          reasoning: action.reasoning,
          type: action.actionType,
        });
        this.store.updateTrustScore(action.category, 3); // Trust grows per action
      }
    }
  }
}
```

### Proactive Actions Definition

```javascript
// ProactiveActions.js
export const PROACTIVE_ACTIONS = [
  {
    name: 'Geyser Pre-heat',
    actionType: 'geyser_preheat',
    triggerTime: 375,  // 06:15 — 45 min before 07:00 alarm
    targetDevice: 'smart_geyser',
    category: 'utility',
    room: 'bath',
    reasoning: 'Family wakes at 07:00. Pre-heating water 45 minutes ahead ensures hot water is ready.',
    announcement: { elder: 'Good morning! Hot water is ready for you.', parent: 'Geyser warmed up for the morning rush.', child: 'Hot water's ready!' },
  },
  {
    name: 'Pre-cooling Living Room',
    actionType: 'ac_precool',
    triggerTime: 1050, // 17:30 — Rajesh returns ~18:00
    targetDevice: 'living_room_ac',
    category: 'climate',
    room: 'livingRoom',
    reasoning: 'Rajesh typically returns at 18:00. Pre-cooling ensures comfortable temperature on arrival.',
    announcement: { parent: 'Cooling the living room before you get home.' },
  },
  {
    name: 'Security Arm',
    actionType: 'security_arm',
    triggerTime: 540,  // 09:00 — After parents leave for work
    targetDevice: 'smart_lock',
    category: 'security',
    room: 'balcony',
    reasoning: 'All adults have departed. Arming security camera and lock for daytime protection.',
    announcement: { elder: 'Security has been armed. You are safe inside.' },
  },
  {
    name: 'Energy Optimization',
    actionType: 'energy_optimization',
    triggerTime: 840,  // 14:00 — Peak tariff period
    targetDevice: 'inverter_ups',
    category: 'power',
    room: 'utility',
    reasoning: 'Peak electricity tariff begins. Shifting non-essential loads to inverter backup.',
    announcement: { parent: 'Switched to inverter for non-essentials to save on peak tariff.' },
  },
  {
    name: 'Comfort Lighting',
    actionType: 'comfort_lighting',
    triggerTime: 1065, // 17:45 — Sunset minus 15 min
    targetDevice: 'smart_lights',
    category: 'lighting',
    room: 'livingRoom',
    reasoning: 'Sunset approaching. Transitioning to warm indoor lighting for comfort.',
    announcement: { elder: 'Turning on warm lights for the evening.' },
  },
];
```

## Animation System

### Device State Change Animations

```javascript
// Effects.js
export class Effects {
  constructor(scene, deviceIndicators) {
    this.scene = scene;
    this.devices = deviceIndicators;
    this.activeAnimations = new Map();
  }

  highlightDevice(deviceId, duration = 2000) {
    const mesh = this.devices.getMesh(deviceId);
    if (!mesh) return;

    const originalEmissive = mesh.material.emissiveIntensity;
    const startTime = performance.now();

    const animate = () => {
      const elapsed = performance.now() - startTime;
      const t = elapsed / duration;

      if (t >= 1) {
        mesh.material.emissiveIntensity = originalEmissive;
        return;
      }

      // Pulse glow effect
      const pulse = Math.sin(t * Math.PI * 4) * 0.5 + 0.5;
      mesh.material.emissiveIntensity = originalEmissive + pulse * 0.8;
      requestAnimationFrame(animate);
    };
    animate();
  }

  powerCutFlicker(duration = 800) {
    const overlay = document.getElementById('flicker-overlay');
    overlay.style.display = 'block';
    let flickerCount = 0;
    const maxFlickers = 4;

    const flicker = () => {
      if (flickerCount >= maxFlickers) {
        overlay.style.display = 'none';
        return;
      }
      overlay.style.opacity = flickerCount % 2 === 0 ? '0.8' : '0';
      flickerCount++;
      setTimeout(flicker, duration / maxFlickers);
    };
    flicker();
  }

  inverterGlow(deviceId) {
    const mesh = this.devices.getMesh(deviceId);
    if (!mesh) return;

    const glowMaterial = mesh.material.clone();
    glowMaterial.emissive.set(0x00ff88);
    glowMaterial.emissiveIntensity = 0.6;
    mesh.material = glowMaterial;

    // Add point light at inverter position
    const light = new THREE.PointLight(0x00ff88, 1, 3);
    light.position.copy(mesh.position);
    this.scene.add(light);
    this.activeAnimations.set('inverter_glow', { mesh, light, originalMaterial: mesh.material });
  }

  dimRooms(roomsToKeepLit) {
    // Reduce emissive on all room lights except prioritized ones
    this.devices.getAllRoomLights().forEach(({ roomId, lightMesh }) => {
      if (!roomsToKeepLit.includes(roomId)) {
        lightMesh.material.emissiveIntensity = 0.02;
        lightMesh.material.opacity = 0.3;
      }
    });
  }
}
```

### Avatar Movement

```javascript
// AvatarManager.js
export class AvatarManager {
  constructor(scene, roomDefinitions) {
    this.scene = scene;
    this.rooms = roomDefinitions;
    this.avatars = new Map();
    this.createAvatars();
  }

  createAvatars() {
    const family = ['rajesh', 'priya', 'arjun', 'ananya', 'dadaji', 'dadiji'];
    const colors = [0xff6b6b, 0x4ecdc4, 0x45b7d1, 0xf7dc6f, 0xbb8fce, 0x82e0aa];

    family.forEach((name, i) => {
      const geometry = new THREE.CapsuleGeometry(0.15, 0.4, 4, 8);
      const material = new THREE.MeshLambertMaterial({ color: colors[i] });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.visible = false;
      this.scene.add(mesh);
      this.avatars.set(name, { mesh, currentRoom: null });
    });
  }

  updatePositions(timeMinutes, schedule) {
    for (const [memberId, slots] of Object.entries(schedule)) {
      const avatar = this.avatars.get(memberId);
      if (!avatar) continue;

      const currentSlot = slots.find(s => timeMinutes >= s.start && timeMinutes < s.end);
      if (!currentSlot || !currentSlot.room) {
        avatar.mesh.visible = false;
        continue;
      }

      avatar.mesh.visible = true;
      const targetPos = this.rooms.getOccupantPosition(currentSlot.room, memberId);

      // Smooth lerp to target position
      avatar.mesh.position.lerp(targetPos, 0.05);
    }
  }
}
```

### Speech Bubble System

```javascript
// SpeechBubble.js
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

export class SpeechBubbleManager {
  constructor(scene, container) {
    this.scene = scene;
    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.setSize(container.clientWidth, container.clientHeight);
    this.labelRenderer.domElement.style.position = 'absolute';
    this.labelRenderer.domElement.style.top = '0';
    this.labelRenderer.domElement.style.pointerEvents = 'none';
    container.appendChild(this.labelRenderer.domElement);
    this.activeBubbles = [];
  }

  show(position, text, duration = 5000) {
    const el = document.createElement('div');
    el.className = 'speech-bubble glass-panel';
    el.textContent = text;

    const label = new CSS2DObject(el);
    label.position.copy(position);
    label.position.y += 1.5; // Float above device
    this.scene.add(label);

    this.activeBubbles.push({ label, el, createdAt: performance.now(), duration });

    // Auto-remove after duration
    setTimeout(() => {
      el.classList.add('fade-out');
      setTimeout(() => {
        this.scene.remove(label);
        this.activeBubbles = this.activeBubbles.filter(b => b.label !== label);
      }, 500);
    }, duration);
  }

  render(camera) {
    this.labelRenderer.render(this.scene, camera);
  }
}
```

## Timeline/Scrubber Implementation

```html
<!-- Timeline HTML structure -->
<div id="timeline-container" class="glass-panel timeline-panel">
  <div class="timeline-controls">
    <button id="play-pause-btn" class="btn-icon">▶</button>
    <span id="time-display" class="time-display">00:00</span>
    <div class="speed-controls">
      <button class="speed-btn" data-speed="1">1x</button>
      <button class="speed-btn" data-speed="10">10x</button>
      <button class="speed-btn active" data-speed="60">60x</button>
      <button class="speed-btn" data-speed="120">120x</button>
    </div>
  </div>
  <div class="scrubber-track">
    <input type="range" id="timeline-scrubber" min="0" max="1439" value="0" step="1" />
    <div class="scrubber-markers">
      <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:59</span>
    </div>
    <div id="event-markers" class="event-markers"></div>
  </div>
</div>
```

```css
/* Timeline styles */
.timeline-panel {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.75rem 1.5rem;
  border-radius: 12px 12px 0 0;
  z-index: 100;
}

.scrubber-track input[type="range"] {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
}

.scrubber-track input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: var(--color-accent);
  border-radius: 50%;
  cursor: grab;
  box-shadow: 0 0 8px rgba(var(--color-accent-rgb), 0.6);
}

.event-markers {
  position: relative;
  height: 8px;
  margin-top: 4px;
}

.event-marker {
  position: absolute;
  width: 4px;
  height: 8px;
  background: var(--color-accent);
  border-radius: 2px;
  opacity: 0.7;
}
```

## Power Cut Scenario Flow

```javascript
// PowerCutScenario.js
export class PowerCutScenario {
  constructor(effects, speechBubbles, eventScheduler, stateStore, eventBus) {
    this.effects = effects;
    this.speechBubbles = speechBubbles;
    this.scheduler = eventScheduler;
    this.store = stateStore;
    this.bus = eventBus;
  }

  trigger(currentTimeMinutes) {
    const stages = [
      { delay: 0, stage: 'SENSE', action: () => this.sense(currentTimeMinutes) },
      { delay: 500, stage: 'THINK', action: () => this.think(currentTimeMinutes) },
      { delay: 1500, stage: 'ACT', action: () => this.act() },
      { delay: 2500, stage: 'EXPLAIN', action: () => this.explain() },
    ];

    stages.forEach(({ delay, stage, action }) => {
      setTimeout(() => {
        this.store.addEventLogEntry({
          time: currentTimeMinutes,
          action: `Power Cut - ${stage}`,
          device: 'inverter_ups',
          reasoning: this.getStageReasoning(stage),
          type: 'power_cut',
          stage,
        });
        action();
      }, delay);
    });
  }

  sense(time) {
    this.effects.powerCutFlicker();
    this.bus.emit(EVENTS.POWER_CUT, { time });
  }

  think(time) {
    // Determine which rooms have active occupants needing power
    const prioritizedRooms = ['studyRoom', 'livingRoom']; // Arjun tuition + Dadaji
    this.store.setDeviceState('inverter_ups', { mode: 'active', load: 65 });
    this.showReasoningPanel(prioritizedRooms);
  }

  act() {
    this.effects.inverterGlow('inverter_ups');
    this.effects.dimRooms(['studyRoom', 'livingRoom']);
  }

  explain() {
    const announcements = [
      { room: 'studyRoom', text: "Power cut detected. Your study room is on backup power — your class won't be interrupted, Arjun." },
      { room: 'livingRoom', text: "Don't worry, Dadaji. Living room lights and fan are running on inverter." },
      { room: 'kitchen', text: "Priya, I've paused the kitchen hub to conserve inverter. Estimated backup: 2.5 hours." },
    ];
    announcements.forEach(a => {
      this.bus.emit(EVENTS.SPEECH_BUBBLE, a);
    });
  }

  showReasoningPanel(prioritizedRooms) {
    const panel = document.getElementById('reasoning-panel');
    panel.classList.remove('hidden');
    panel.innerHTML = `
      <div class="glass-panel reasoning-content">
        <h3>⚡ Power Cut — Alexa's Reasoning</h3>
        <div class="reasoning-steps">
          <p><strong>Context:</strong> Arjun's tuition active in Study Room, Dadaji resting in Living Room</p>
          <p><strong>Priority:</strong> Wi-Fi + Study Room (education) > Living Room (elderly comfort) > Others</p>
          <p><strong>Action:</strong> Inverter allocated to priority rooms. AC, geyser, kitchen hub paused.</p>
          <p><strong>Estimate:</strong> 2.5 hours at current load. Tuition ends at 18:30 — sufficient.</p>
        </div>
      </div>
    `;
  }
}
```

## Performance Considerations

### Geometry Budget

| Element | Estimated Triangles | Strategy |
|---------|-------------------|----------|
| House walls (exterior + interior) | ~4,000 | Merged BufferGeometry, no subdivision |
| Floor | ~200 | Single box |
| Roof (cutaway) | ~1,000 | Simple slope geometry |
| Furniture (all rooms) | ~8,000 | Box/cylinder primitives only |
| Device indicators (×10) | ~2,000 | Sphere/cylinder, 8 segments |
| Family avatars (×6) | ~1,800 | CapsuleGeometry, 4 cap segments |
| Decorative elements | ~3,000 | Minimal props |
| **Total** | **~20,000** | Well under 50,000 budget |

### Render Optimization Strategies

1. **Geometry merging** — Static house walls merged into single BufferGeometry to reduce draw calls
2. **Low segment counts** — Spheres use 8×6 segments, cylinders use 8 segments
3. **Shared materials** — Material instances shared across same-type meshes via a material cache
4. **Frustum culling** — Three.js default frustum culling left enabled
5. **Shadow map optimization** — Single directional light with 1024×1024 shadow map, PCFSoft
6. **Pixel ratio capping** — `Math.min(window.devicePixelRatio, 2)` prevents 3x+ rendering on high-DPI
7. **CSS2DRenderer for overlays** — Speech bubbles use DOM elements instead of 3D geometry
8. **requestAnimationFrame** — Single RAF loop drives both Three.js render and simulation tick
9. **Conditional updates** — Avatar positions only lerp when visible; lighting recalculates only when time changes by ≥1 minute

### Bundle Optimization

```javascript
// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    target: 'esnext',
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          'three-addons': ['three/addons/controls/OrbitControls.js', 'three/addons/renderers/CSS2DRenderer.js'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ['three'],
  },
});
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| Real API unreachable | Show toast notification, auto-fallback to Mock mode |
| WebGL not supported | Display fallback message with system requirements |
| Browser resize during render | Debounced resize handler updates camera aspect and renderer size |
| Invalid event form data | Inline validation messages, prevent submission |
| Simulation reaches 23:59 | Auto-pause, show "Day Complete" overlay |
| Three.js texture load failure | Use flat-color fallback materials |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Data layer mode routing

*For any* data operation invoked on the DataLayer, when the mode is set to 'mock', the operation SHALL return data without making any HTTP network requests; and when the mode is set to 'real', the operation SHALL make an HTTP request to `http://localhost:8080`.

**Validates: Requirements 2.3, 2.4**

### Property 2: Mock data schema conformance

*For any* API endpoint in the defined set (devices, device state, context snapshot, patterns, autonomy tiers), the mock provider's response SHALL conform to the same data structure (same keys, same value types) as the documented API response schema.

**Validates: Requirements 2.1**

### Property 3: No backward phase navigation

*For any* sequence of user interactions while in the Deployment Phase, the application phase SHALL remain 'deployment' and SHALL NOT revert to 'learning' unless an explicit page reload or reset action is triggered.

**Validates: Requirements 3.4**

### Property 4: Event addition grows list

*For any* valid event data (non-empty type, valid time, valid room), submitting it via the event form SHALL increase the event list length by exactly one, and the new event SHALL be present in the list.

**Validates: Requirements 4.5**

### Property 5: Event removal shrinks list

*For any* event currently in the event list, removing it SHALL decrease the list length by exactly one, and the removed event SHALL no longer be present in the list.

**Validates: Requirements 4.6**

### Property 6: Avatar position matches schedule

*For any* simulation time T (0–1439) and any family member with a defined schedule entry for time T that specifies a room, the corresponding avatar's position SHALL be within the bounding box of that room.

**Validates: Requirements 6.2**

### Property 7: Speed multiplier clock advancement

*For any* speed multiplier S in {1, 10, 60, 120} and any elapsed real-time interval of T milliseconds, the simulation clock SHALL advance by approximately (T / 1000) × (S / 60) simulated minutes (within a tolerance of ±1 minute due to frame timing).

**Validates: Requirements 7.5, 14.1, 14.2, 14.3, 14.4**

### Property 8: Scrubber-simulation time bidirectional sync

*For any* valid time position P (0–1439 minutes), setting the timeline scrubber to position P SHALL update the simulation clock to P; and for any simulation clock value C, the scrubber's visual position SHALL correspond to C.

**Validates: Requirements 7.6, 14.5**

### Property 9: Pause and resume controls clock

*For any* simulation state where the clock is running, invoking pause SHALL stop the clock from advancing (delta = 0 over any real-time interval); and invoking resume SHALL restart clock advancement at the previously set speed multiplier.

**Validates: Requirements 14.6**

### Property 10: Event log entries contain required fields

*For any* proactive action event that fires, the resulting Event Log entry SHALL contain a non-empty action name, a non-empty target device identifier, a non-empty reasoning summary, and a valid timestamp (0–1439).

**Validates: Requirements 8.1**

### Property 11: Trust score maps to correct tier

*For any* trust score value V in the range [0, 100], the computed autonomy tier SHALL be: 1 if V ∈ [0, 20], 2 if V ∈ [21, 45], 3 if V ∈ [46, 70], 4 if V ∈ [71, 90], 5 if V ∈ [91, 100].

**Validates: Requirements 9.3**

### Property 12: Lighting matches time of day

*For any* simulation time T in [06:30, 17:30] (fully daytime), the ambient light intensity SHALL be ≥ 0.5 with warm tones; and for any T in [18:30, 05:30] (fully nighttime), the ambient light intensity SHALL be ≤ 0.2 with cool blue tones.

**Validates: Requirements 10.1, 10.2**

### Property 13: Lighting transition interpolation

*For any* simulation time T within the 30-minute transition windows (05:30–06:30 sunrise, 17:30–18:30 sunset), the lighting intensity SHALL be strictly between the nighttime minimum and daytime maximum, monotonically increasing during sunrise and monotonically decreasing during sunset.

**Validates: Requirements 10.3**

### Property 14: Speech bubble lifetime

*For any* speech bubble created in the scene, it SHALL remain visible for exactly 5000 milliseconds (±500ms tolerance for animation frame timing) before beginning its fade-out removal.

**Validates: Requirements 11.3**

### Property 15: Total triangle budget

*For all* geometries present in the Three.js scene at any point during execution, the sum of all triangle counts SHALL be less than 50,000.

**Validates: Requirements 15.2**

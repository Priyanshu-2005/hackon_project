/**
 * FloorPlan2D — Pure CSS/DOM-based 2D cutaway house for the Sharma family.
 * Replaces the Three.js 3D scene (SceneManager, HouseBuilder, DeviceIndicators,
 * LightingSystem, AvatarManager, SpeechBubble, Effects).
 *
 * Layout (cutaway):
 * ┌─────────────── roof shell ───────────────┐
 * │ Master Bedroom │ Study Room │ Kitchen    │
 * ├───────────────┬┴────────────┼────────────┤
 * │ Living Room   │ Bath        │ Kids │Bal. │
 * └───────────────┴─────────────┴──────┴─────┘
 */

import { FAMILY_SCHEDULE } from '../data/FamilySchedule.js';

// ─── Room Layout (cutaway house percentages) ─────────────────────
const ROOM_LAYOUT = {
  master_bedroom: { top: 0, left: 0, width: 33, height: 42, name: 'Master Bedroom', color: '#1f2636' },
  study_room: { top: 0, left: 33, width: 27, height: 42, name: 'Study Room', color: '#182a2f' },
  kitchen: { top: 0, left: 60, width: 40, height: 42, name: 'Kitchen', color: '#262117' },
  living_room: { top: 42, left: 0, width: 42, height: 58, name: 'Living Room', color: '#172432' },
  bath: { top: 42, left: 42, width: 20, height: 58, name: 'Bath', color: '#122a30' },
  kids_room: { top: 42, left: 62, width: 23, height: 58, name: 'Kids Room', color: '#232133' },
  balcony: { top: 42, left: 85, width: 15, height: 58, name: 'Balcony', color: '#152522' },
};

// ─── Device Placements (% offsets within room) ───────────────────
const DEVICE_PLACEMENTS = {
  living_room_ac: { room: 'living_room', x: 85, y: 15, icon: '❄️', label: 'AC' },
  smart_tv: { room: 'living_room', x: 22, y: 38, icon: '📺', label: 'TV' },
  echo_living: { room: 'living_room', x: 62, y: 74, icon: '🔊', label: 'Echo' },
  kitchen_hub: { room: 'kitchen', x: 70, y: 46, icon: '🍳', label: 'Hub' },
  water_purifier: { room: 'kitchen', x: 25, y: 82, icon: '💧', label: 'Purifier' },
  security_camera: { room: 'balcony', x: 55, y: 22, icon: '📷', label: 'Camera' },
  smart_lock: { room: 'balcony', x: 50, y: 64, icon: '🔒', label: 'Lock' },
  smart_geyser: { room: 'bath', x: 48, y: 42, icon: '🚿', label: 'Geyser' },
  inverter_ups: { room: 'kitchen', x: 86, y: 82, icon: '🔋', label: 'Inverter' },
  echo_study: { room: 'study_room', x: 60, y: 58, icon: '🔊', label: 'Echo' },
  echo_kids: { room: 'kids_room', x: 54, y: 66, icon: '🔊', label: 'Echo' },
  // Smart lights — one per room
  smart_lights_living_room: { room: 'living_room', x: 50, y: 14, icon: '💡', label: 'Light' },
  smart_lights_master_bedroom: { room: 'master_bedroom', x: 50, y: 16, icon: '💡', label: 'Light' },
  smart_lights_kitchen: { room: 'kitchen', x: 55, y: 16, icon: '💡', label: 'Light' },
  smart_lights_bath: { room: 'bath', x: 26, y: 16, icon: '💡', label: 'Light' },
  smart_lights_study_room: { room: 'study_room', x: 50, y: 16, icon: '💡', label: 'Light' },
  smart_lights_kids_room: { room: 'kids_room', x: 50, y: 16, icon: '💡', label: 'Light' },
  smart_lights_balcony: { room: 'balcony', x: 50, y: 40, icon: '💡', label: 'Light' },
};

const DEVICE_DEFAULT_STATES = {
  living_room_ac: { active: false, onLabel: 'Cooling', offLabel: 'Off' },
  smart_tv: { active: false, onLabel: 'Playing', offLabel: 'Off' },
  echo_living: { active: true, onLabel: 'Online', offLabel: 'Muted' },
  kitchen_hub: { active: true, onLabel: 'Ready', offLabel: 'Paused' },
  water_purifier: { active: true, onLabel: 'Filtering', offLabel: 'Off' },
  security_camera: { active: true, onLabel: 'Recording', offLabel: 'Idle' },
  smart_lock: { active: true, onLabel: 'Locked', offLabel: 'Unlocked' },
  smart_geyser: { active: false, onLabel: 'Heating', offLabel: 'Off' },
  inverter_ups: { active: false, onLabel: 'Backup', offLabel: 'Standby' },
  echo_study: { active: true, onLabel: 'Online', offLabel: 'Muted' },
  echo_kids: { active: true, onLabel: 'Online', offLabel: 'Muted' },
};

const ROOM_DECOR = {
  master_bedroom: [
    { type: 'window', x: 9, y: 16, w: 16, h: 18 },
    { type: 'bed', x: 10, y: 58, w: 42, h: 24 },
    { type: 'side-table', x: 54, y: 62, w: 12, h: 16 },
    { type: 'lamp', x: 59, y: 49, w: 7, h: 17 },
    { type: 'picture', x: 72, y: 24, w: 12, h: 16 },
  ],
  study_room: [
    { type: 'window', x: 10, y: 14, w: 18, h: 17 },
    { type: 'bookshelf', x: 12, y: 40, w: 20, h: 42 },
    { type: 'desk', x: 47, y: 58, w: 40, h: 18 },
    { type: 'chair', x: 57, y: 70, w: 13, h: 16 },
    { type: 'plant', x: 84, y: 60, w: 8, h: 24 },
  ],
  kitchen: [
    { type: 'window', x: 8, y: 14, w: 16, h: 17 },
    { type: 'cabinet', x: 38, y: 16, w: 45, h: 18 },
    { type: 'counter', x: 9, y: 65, w: 78, h: 17 },
    { type: 'stove', x: 48, y: 52, w: 18, h: 18 },
    { type: 'sink', x: 21, y: 55, w: 16, h: 12 },
  ],
  living_room: [
    { type: 'window', x: 8, y: 12, w: 14, h: 17 },
    { type: 'tv-unit', x: 10, y: 48, w: 24, h: 20 },
    { type: 'sofa', x: 45, y: 58, w: 38, h: 22 },
    { type: 'coffee-table', x: 47, y: 79, w: 22, h: 8 },
    { type: 'plant', x: 86, y: 48, w: 7, h: 24 },
  ],
  bath: [
    { type: 'vent', x: 13, y: 14, w: 16, h: 10 },
    { type: 'geyser-tank', x: 50, y: 24, w: 22, h: 22 },
    { type: 'sink-basin', x: 16, y: 69, w: 18, h: 17 },
    { type: 'shower', x: 69, y: 57, w: 15, h: 30 },
  ],
  kids_room: [
    { type: 'window', x: 10, y: 13, w: 18, h: 17 },
    { type: 'bunk-bed', x: 9, y: 51, w: 32, h: 32 },
    { type: 'toy-shelf', x: 58, y: 44, w: 27, h: 24 },
    { type: 'rug', x: 45, y: 78, w: 35, h: 12 },
  ],
  balcony: [
    { type: 'railing', x: 8, y: 18, w: 84, h: 14 },
    { type: 'water-tank', x: 20, y: 42, w: 54, h: 27 },
    { type: 'plant', x: 73, y: 66, w: 12, h: 22 },
  ],
};

// Alias canonical IDs
const DEVICE_ALIASES = {
  echo_devices: 'echo_living',
  smart_lights: 'smart_lights_living_room',
};

// ─── Family avatar colors ────────────────────────────────────────
const AVATAR_COLORS = {
  rajesh: '#ff6b6b',
  priya: '#4ecdc4',
  arjun: '#45b7d1',
  ananya: '#f7dc6f',
  dadaji: '#bb8fce',
  dadiji: '#82e0aa',
};

/**
 * FloorPlan2D renders an interactive 2D floor plan.
 */
export class FloorPlan2D {
  constructor(containerEl) {
    this.container = containerEl;
    this.container.innerHTML = '';

    /** @type {Map<string, HTMLElement>} roomId → room div */
    this.roomEls = new Map();
    /** @type {Map<string, HTMLElement>} deviceId → device div */
    this.deviceEls = new Map();
    /** @type {Map<string, HTMLElement>} memberId → avatar dot */
    this.avatarEls = new Map();
    /** @type {Map<string, HTMLElement>} active speech bubble elements */
    this.speechBubbles = new Map();
    /** @type {Map<string, { active: boolean }>} deviceId → local interactive state */
    this.deviceStates = new Map();
    /** @type {string|null} */
    this.selectedDeviceId = null;
    /** @type {HTMLElement|null} */
    this.roomLayer = null;

    this._injectStyles();
    this._initializeDeviceStates();
    this._buildFloorPlan();
    this._buildDevices();
    this._buildAvatars();
    this.updateAvatars(0);
    this.updateLighting(0);
  }

  // ═══════════════════════════════════════════════════════════════
  // Public API
  // ═══════════════════════════════════════════════════════════════

  /**
   * Update avatar positions based on simulation time.
   * @param {number} timeMinutes - Current time in minutes (0-1439)
   */
  updateAvatars(timeMinutes) {
    for (const [memberId, schedule] of Object.entries(FAMILY_SCHEDULE)) {
      const dot = this.avatarEls.get(memberId);
      if (!dot) continue;

      const entry = schedule.find(s => timeMinutes >= s.start && timeMinutes < s.end);
      const roomId = entry ? entry.room : null;

      if (!roomId) {
        dot.style.display = 'none';
      } else {
        dot.style.display = 'block';
        const roomEl = this.roomEls.get(roomId);
        if (roomEl) {
          // Position avatar within the room
          this._positionAvatarInRoom(dot, memberId, roomId, timeMinutes);
        }
      }
    }
  }

  /**
   * Update lighting (day/night visual).
   * @param {number} timeMinutes - Current time in minutes (0-1439)
   */
  updateLighting(timeMinutes) {
    const planEl = this.container.querySelector('.floor-plan-wrapper');
    if (!planEl) return;

    // Day (6:00–18:00) is warm, night is cool
    let warmth = 0;
    if (timeMinutes < 360) {
      warmth = 0; // night
    } else if (timeMinutes < 420) {
      warmth = (timeMinutes - 360) / 60; // sunrise transition
    } else if (timeMinutes < 1020) {
      warmth = 1; // day
    } else if (timeMinutes < 1080) {
      warmth = 1 - (timeMinutes - 1020) / 60; // sunset transition
    } else {
      warmth = 0; // night
    }

    // Adjust overall brightness and hue
    const brightness = 0.7 + warmth * 0.3;
    const hueRotate = (1 - warmth) * 10; // slight blue shift at night
    planEl.style.filter = `brightness(${brightness}) hue-rotate(${hueRotate}deg)`;
  }

  /**
   * Highlight a device with a pulse glow.
   * @param {string} deviceId - Device identifier
   * @param {number} [duration=2000] - Duration in ms
   */
  highlightDevice(deviceId, duration = 2000) {
    const resolvedId = DEVICE_ALIASES[deviceId] || deviceId;
    const el = this.deviceEls.get(resolvedId);
    if (!el) return;

    el.classList.add('device-highlight');
    // Also glow the room
    const placement = DEVICE_PLACEMENTS[resolvedId];
    if (placement) {
      const roomEl = this.roomEls.get(placement.room);
      if (roomEl) {
        roomEl.classList.add('room-highlight');
        setTimeout(() => roomEl.classList.remove('room-highlight'), duration);
      }
    }
    setTimeout(() => el.classList.remove('device-highlight'), duration);
  }

  /**
   * Show a speech bubble near a device.
   * @param {string} deviceId - Device identifier
   * @param {string} text - Message text
   * @param {number} [duration=5000] - Duration in ms
   */
  showSpeechBubble(deviceId, text, duration = 5000) {
    const resolvedId = DEVICE_ALIASES[deviceId] || deviceId;
    const el = this.deviceEls.get(resolvedId);
    if (!el) return;

    // Remove existing bubble for this device
    const existingBubble = this.speechBubbles.get(resolvedId);
    if (existingBubble) existingBubble.remove();

    const bubble = document.createElement('div');
    bubble.className = 'fp-speech-bubble';
    bubble.textContent = text;
    el.appendChild(bubble);
    this.speechBubbles.set(resolvedId, bubble);

    // Animate in
    requestAnimationFrame(() => bubble.classList.add('visible'));

    setTimeout(() => {
      bubble.classList.remove('visible');
      setTimeout(() => {
        bubble.remove();
        this.speechBubbles.delete(resolvedId);
      }, 300);
    }, duration);
  }

  /**
   * Compatibility wrapper for callers that expect SpeechBubbleManager.show().
   * @param {string|object} target - Device ID or ignored position object
   * @param {string} text - Message text
   * @param {number} [duration=5000] - Duration in ms
   */
  show(target, text, duration = 5000) {
    const deviceId = typeof target === 'string' ? target : 'echo_living';
    this.showSpeechBubble(deviceId, text, duration);
  }

  /**
   * Dim rooms for power cut. Keep specified rooms lit.
   * @param {string[]} roomsToKeepLit - Room IDs to keep lit
   */
  dimRooms(roomsToKeepLit) {
    for (const [roomId, roomEl] of this.roomEls) {
      if (roomsToKeepLit.includes(roomId)) {
        roomEl.classList.add('room-powered');
      } else {
        roomEl.classList.add('room-dimmed');
      }
    }
  }

  /**
   * Restore all rooms from power cut.
   */
  restoreAll() {
    for (const [, roomEl] of this.roomEls) {
      roomEl.classList.remove('room-dimmed', 'room-powered', 'room-highlight');
    }
    for (const [, deviceEl] of this.deviceEls) {
      deviceEl.classList.remove('device-highlight', 'inverter-active');
    }
  }

  /**
   * Alias for restoreAll (used by Effects interface).
   */
  restoreRooms() {
    this.restoreAll();
  }

  /**
   * Flash effect for power cut (flicker overlay).
   */
  powerCutFlicker() {
    const overlay = document.getElementById('flicker-overlay');
    if (!overlay) return;

    overlay.style.display = 'block';
    overlay.style.opacity = '0';

    const duration = 800;
    const flickerCount = 4;
    const cycleTime = duration / flickerCount;
    const startTime = performance.now();

    const animate = () => {
      const elapsed = performance.now() - startTime;
      if (elapsed >= duration) {
        overlay.style.display = 'none';
        overlay.style.opacity = '0';
        return;
      }
      const flickerIndex = Math.floor(elapsed / cycleTime);
      overlay.style.opacity = flickerIndex % 2 === 0 ? '0.8' : '0';
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }

  /**
   * Green glow on inverter (used by PowerCutScenario).
   * @param {string} deviceId
   */
  inverterGlow(deviceId) {
    const resolvedId = DEVICE_ALIASES[deviceId] || deviceId;
    const el = this.deviceEls.get(resolvedId);
    if (!el) return;
    el.classList.add('inverter-active');
  }

  /**
   * Get device position for external use (returns { x, y } in pixels relative to container).
   * @param {string} deviceId
   * @returns {{ x: number, y: number, clone: Function }|undefined}
   */
  getDevicePosition(deviceId) {
    const resolvedId = DEVICE_ALIASES[deviceId] || deviceId;
    const el = this.deviceEls.get(resolvedId);
    if (!el) return undefined;
    const rect = el.getBoundingClientRect();
    const containerRect = this.container.getBoundingClientRect();
    const pos = {
      x: rect.left - containerRect.left + rect.width / 2,
      y: rect.top - containerRect.top + rect.height / 2,
    };
    pos.clone = () => ({ ...pos, clone: pos.clone });
    return pos;
  }

  /**
   * Get mesh-like interface for PowerCutScenario compatibility.
   * @param {string} deviceId
   * @returns {{ position: { x: number, y: number, clone: Function }}|undefined}
   */
  getMesh(deviceId) {
    const pos = this.getDevicePosition(deviceId);
    if (!pos) return undefined;
    return { position: pos };
  }

  /**
   * Get all room lights (compatibility with DeviceIndicators interface).
   * @returns {Array<{ roomId: string, lightMesh: object }>}
   */
  getAllRoomLights() {
    const lights = [];
    for (const [roomId] of this.roomEls) {
      lights.push({ roomId, lightMesh: { material: {} } });
    }
    return lights;
  }

  // ═══════════════════════════════════════════════════════════════
  // Private: Build DOM
  // ═══════════════════════════════════════════════════════════════

  _initializeDeviceStates() {
    for (const deviceId of Object.keys(DEVICE_PLACEMENTS)) {
      const defaults = DEVICE_DEFAULT_STATES[deviceId];
      const isSmartLight = deviceId.startsWith('smart_lights_');
      this.deviceStates.set(deviceId, {
        active: defaults ? defaults.active : isSmartLight,
      });
    }
  }

  _buildFloorPlan() {
    const wrapper = document.createElement('div');
    wrapper.className = 'floor-plan-wrapper';

    const skyline = document.createElement('div');
    skyline.className = 'fp-skyline';

    const title = document.createElement('div');
    title.className = 'fp-house-title';
    title.innerHTML = `
      <span class="fp-title-small">Sharma Smart Home</span>
      <strong>Alexa Thinks Ahead</strong>
    `;

    const roof = document.createElement('div');
    roof.className = 'fp-roof';
    roof.innerHTML = `
      <span class="fp-roof-ridge"></span>
      <span class="fp-chimney"></span>
      <span class="fp-dish"></span>
    `;

    const shell = document.createElement('div');
    shell.className = 'fp-house-shell';

    const roomLayer = document.createElement('div');
    roomLayer.className = 'fp-room-layer';
    this.roomLayer = roomLayer;

    for (const [roomId, layout] of Object.entries(ROOM_LAYOUT)) {
      const roomEl = document.createElement('div');
      roomEl.className = `fp-room fp-room-${roomId}`;
      roomEl.dataset.roomId = roomId;
      roomEl.style.top = `${layout.top}%`;
      roomEl.style.left = `${layout.left}%`;
      roomEl.style.width = `${layout.width}%`;
      roomEl.style.height = `${layout.height}%`;
      roomEl.style.setProperty('--room-base', layout.color);

      const backWall = document.createElement('div');
      backWall.className = 'fp-room-backwall';
      roomEl.appendChild(backWall);

      const decorLayer = document.createElement('div');
      decorLayer.className = 'fp-room-decor';
      this._buildRoomDecor(roomId, decorLayer);
      roomEl.appendChild(decorLayer);

      const floor = document.createElement('div');
      floor.className = 'fp-room-floor';
      roomEl.appendChild(floor);

      const label = document.createElement('span');
      label.className = 'fp-room-label';
      label.textContent = layout.name;
      roomEl.appendChild(label);

      roomEl.addEventListener('click', (event) => this._onRoomClick(roomId, event));

      roomLayer.appendChild(roomEl);
      this.roomEls.set(roomId, roomEl);
    }

    shell.appendChild(roomLayer);

    const foundation = document.createElement('div');
    foundation.className = 'fp-foundation';

    // Family legend — explains the colored dots moving between rooms
    const legend = document.createElement('div');
    legend.className = 'fp-legend';
    legend.innerHTML = `
      <span class="fp-legend-title">Family</span>
      ${Object.entries(AVATAR_COLORS).map(([id, color]) => {
        const name = id.charAt(0).toUpperCase() + id.slice(1);
        return `<span class="fp-legend-item"><span class="fp-legend-dot" style="background:${color}">${name.charAt(0)}</span>${name}</span>`;
      }).join('')}
    `;

    wrapper.appendChild(skyline);
    wrapper.appendChild(title);
    wrapper.appendChild(roof);
    wrapper.appendChild(shell);
    wrapper.appendChild(foundation);
    wrapper.appendChild(legend);
    this.container.appendChild(wrapper);
  }

  _buildRoomDecor(roomId, decorLayer) {
    const decorItems = ROOM_DECOR[roomId] || [];
    for (const item of decorItems) {
      const decorEl = document.createElement('span');
      decorEl.className = `fp-prop fp-prop-${item.type}`;
      decorEl.setAttribute('aria-hidden', 'true');
      decorEl.style.left = `${item.x}%`;
      decorEl.style.top = `${item.y}%`;
      decorEl.style.width = `${item.w}%`;
      decorEl.style.height = `${item.h}%`;
      decorLayer.appendChild(decorEl);
    }
  }

  _buildDevices() {
    for (const [deviceId, placement] of Object.entries(DEVICE_PLACEMENTS)) {
      const roomEl = this.roomEls.get(placement.room);
      if (!roomEl) continue;

      const roomName = ROOM_LAYOUT[placement.room]?.name || placement.room;
      const deviceEl = document.createElement('button');
      deviceEl.type = 'button';
      deviceEl.className = 'fp-device';
      deviceEl.dataset.deviceId = deviceId;
      deviceEl.style.left = `${placement.x}%`;
      deviceEl.style.top = `${placement.y}%`;
      deviceEl.title = `${placement.label} in ${roomName}`;
      deviceEl.setAttribute('aria-label', `${placement.label} in ${roomName}`);

      const iconSpan = document.createElement('span');
      iconSpan.className = 'fp-device-icon';
      iconSpan.setAttribute('aria-hidden', 'true');
      iconSpan.textContent = placement.icon;
      deviceEl.appendChild(iconSpan);

      const labelSpan = document.createElement('span');
      labelSpan.className = 'fp-device-label';
      labelSpan.textContent = placement.label;
      deviceEl.appendChild(labelSpan);

      deviceEl.addEventListener('click', (event) => this._onDeviceClick(deviceId, event));

      roomEl.appendChild(deviceEl);
      this.deviceEls.set(deviceId, deviceEl);
      this._applyDeviceState(deviceId);
    }
  }

  _buildAvatars() {
    for (const [memberId, color] of Object.entries(AVATAR_COLORS)) {
      const dot = document.createElement('div');
      dot.className = 'fp-avatar';
      dot.dataset.memberId = memberId;
      dot.style.backgroundColor = color;
      dot.style.display = 'none';
      const displayName = memberId.charAt(0).toUpperCase() + memberId.slice(1);
      dot.title = displayName;
      // Show the member's first initial inside the dot for clarity
      dot.textContent = displayName.charAt(0);

      // Append to the same percentage coordinate layer as rooms.
      const layer = this.roomLayer || this.container.querySelector('.fp-room-layer');
      if (layer) layer.appendChild(dot);
      this.avatarEls.set(memberId, dot);
    }
  }

  _positionAvatarInRoom(dot, memberId, roomId, _timeMinutes) {
    const layout = ROOM_LAYOUT[roomId];
    if (!layout) return;

    // Deterministic offset based on member name
    let hash = 0;
    for (let i = 0; i < memberId.length; i++) {
      hash = (hash * 31 + memberId.charCodeAt(i)) | 0;
    }
    const offsetX = 20 + (((hash & 0xff) / 255) * 60); // 20%-80% within room
    const offsetY = 25 + ((((hash >>> 8) & 0xff) / 255) * 50); // 25%-75% within room

    // Calculate absolute position within the plan
    const absX = layout.left + (layout.width * offsetX) / 100;
    const absY = layout.top + (layout.height * offsetY) / 100;

    dot.style.left = `${absX}%`;
    dot.style.top = `${absY}%`;
  }

  _onRoomClick(roomId, event) {
    if (event?.target?.closest?.('.fp-device')) return;

    const layout = ROOM_LAYOUT[roomId];
    if (!layout) return;

    // Gather devices in room
    const devices = Object.entries(DEVICE_PLACEMENTS)
      .filter(([, p]) => p.room === roomId)
      .map(([id, p]) => ({
        id,
        icon: p.icon,
        label: p.label,
        status: this._getDeviceStateLabel(id),
      }));

    // Gather people in room (check current avatars)
    const people = [];
    for (const [memberId, dot] of this.avatarEls) {
      if (dot.style.display !== 'none') {
        // Check if avatar is positioned in this room
        const avatarLeft = parseFloat(dot.style.left);
        const avatarTop = parseFloat(dot.style.top);
        if (
          avatarLeft >= layout.left &&
          avatarLeft <= layout.left + layout.width &&
          avatarTop >= layout.top &&
          avatarTop <= layout.top + layout.height
        ) {
          people.push(memberId.charAt(0).toUpperCase() + memberId.slice(1));
        }
      }
    }

    // Show info tooltip
    this._showRoomInfo(roomId, layout.name, devices, people);
  }

  _showRoomInfo(roomId, roomName, devices, people) {
    this._removeInfoPanels();
    if (this.selectedDeviceId) {
      this.deviceEls.get(this.selectedDeviceId)?.classList.remove('selected');
      this.selectedDeviceId = null;
    }

    const info = document.createElement('div');
    info.className = 'fp-room-info glass-panel';
    info.innerHTML = `
      <h3>${roomName}</h3>
      <div class="fp-room-info-section">
        <strong>Components</strong>
        <div class="fp-room-info-devices">
          ${devices.length ? devices.map(device => `
            <button type="button" class="fp-component-row" data-device-id="${device.id}">
              <span class="fp-component-row-icon" aria-hidden="true">${device.icon}</span>
              <span class="fp-component-row-label">${device.label}</span>
              <span class="fp-component-row-status">${device.status}</span>
            </button>
          `).join('') : '<span class="fp-empty">None</span>'}
        </div>
      </div>
      <div class="fp-room-info-section">
        <strong>People</strong>
        <div>${people.length ? people.join(', ') : 'None'}</div>
      </div>
      <button class="fp-room-info-close">✕</button>
    `;

    info.querySelector('.fp-room-info-close').addEventListener('click', () => info.remove());
    info.addEventListener('click', (event) => {
      const componentButton = event.target.closest('[data-device-id]');
      if (!componentButton) return;
      this._onDeviceClick(componentButton.dataset.deviceId, event);
    });

    this.container.appendChild(info);
  }

  _onDeviceClick(deviceId, event) {
    event?.stopPropagation();
    const resolvedId = DEVICE_ALIASES[deviceId] || deviceId;
    const placement = DEVICE_PLACEMENTS[resolvedId];
    if (!placement) return;

    if (this.selectedDeviceId && this.selectedDeviceId !== resolvedId) {
      this.deviceEls.get(this.selectedDeviceId)?.classList.remove('selected');
    }

    this.selectedDeviceId = resolvedId;
    this.deviceEls.get(resolvedId)?.classList.add('selected');
    this.highlightDevice(resolvedId, 1200);
    this._showDeviceInfo(resolvedId);
  }

  _showDeviceInfo(deviceId) {
    this._removeInfoPanels();

    const placement = DEVICE_PLACEMENTS[deviceId];
    const room = ROOM_LAYOUT[placement.room];
    const stateLabel = this._getDeviceStateLabel(deviceId);

    const info = document.createElement('div');
    info.className = 'fp-component-info glass-panel';
    info.innerHTML = `
      <button class="fp-room-info-close" type="button" aria-label="Close">✕</button>
      <div class="fp-component-info-heading">
        <span class="fp-component-info-icon" aria-hidden="true">${placement.icon}</span>
        <div>
          <h3>${placement.label}</h3>
          <p>${room?.name || placement.room}</p>
        </div>
      </div>
      <div class="fp-component-status">
        <span>Status</span>
        <strong>${stateLabel}</strong>
      </div>
      <div class="fp-component-actions">
        <button type="button" class="fp-component-action" data-action="toggle">Toggle</button>
        <button type="button" class="fp-component-action" data-action="announce">Announce</button>
      </div>
    `;

    info.querySelector('.fp-room-info-close').addEventListener('click', () => {
      info.remove();
      this.deviceEls.get(deviceId)?.classList.remove('selected');
      if (this.selectedDeviceId === deviceId) this.selectedDeviceId = null;
    });

    info.addEventListener('click', (event) => {
      const actionButton = event.target.closest('[data-action]');
      if (!actionButton) return;
      const action = actionButton.dataset.action;
      if (action === 'toggle') {
        this._toggleDeviceState(deviceId);
      } else if (action === 'announce') {
        this.showSpeechBubble(deviceId, `${placement.label} is ${this._getDeviceStateLabel(deviceId)}.`, 3000);
      }
    });

    this.container.appendChild(info);
  }

  _toggleDeviceState(deviceId) {
    const state = this.deviceStates.get(deviceId) || { active: true };
    this.deviceStates.set(deviceId, { ...state, active: !state.active });
    this._applyDeviceState(deviceId);
    this.highlightDevice(deviceId, 800);
    this._showDeviceInfo(deviceId);
  }

  _applyDeviceState(deviceId) {
    const deviceEl = this.deviceEls.get(deviceId);
    if (!deviceEl) return;

    const state = this.deviceStates.get(deviceId) || { active: true };
    deviceEl.dataset.state = state.active ? 'on' : 'off';
    deviceEl.classList.toggle('is-off', !state.active);
  }

  _getDeviceStateLabel(deviceId) {
    const state = this.deviceStates.get(deviceId) || { active: true };
    const defaults = DEVICE_DEFAULT_STATES[deviceId] || {};
    const isSmartLight = deviceId.startsWith('smart_lights_');
    if (state.active) return defaults.onLabel || (isSmartLight ? 'On' : 'Active');
    return defaults.offLabel || 'Off';
  }

  _removeInfoPanels() {
    this.container.querySelectorAll('.fp-room-info, .fp-component-info').forEach((el) => el.remove());
  }

  // ═══════════════════════════════════════════════════════════════
  // Private: Inject CSS
  // ═══════════════════════════════════════════════════════════════

  _injectStyles() {
    if (document.getElementById('floor-plan-2d-styles')) return;

    const style = document.createElement('style');
    style.id = 'floor-plan-2d-styles';
    style.textContent = `
      .floor-plan-wrapper {
        position: relative;
        width: min(100%, 1180px);
        height: min(100%, 760px);
        min-height: 420px;
        background:
          radial-gradient(circle at 14% 12%, rgba(255, 213, 122, 0.12), transparent 18%),
          radial-gradient(circle at 84% 10%, rgba(0, 202, 255, 0.16), transparent 18%),
          linear-gradient(180deg, #08121c 0%, #0b1118 56%, #070b10 100%);
        border: 1px solid rgba(0, 202, 255, 0.12);
        border-radius: 8px;
        overflow: visible;
        transition: filter 0.5s ease;
        box-shadow:
          inset 0 0 70px rgba(0, 202, 255, 0.05),
          0 18px 70px rgba(0, 0, 0, 0.38);
      }

      .fp-skyline {
        position: absolute;
        inset: 0;
        pointer-events: none;
        overflow: hidden;
        border-radius: inherit;
      }

      .fp-skyline::before,
      .fp-skyline::after {
        content: '';
        position: absolute;
        bottom: 5%;
        width: 34%;
        height: 18%;
        background: linear-gradient(180deg, rgba(29, 57, 68, 0.28), rgba(7, 12, 18, 0));
        clip-path: polygon(0 100%, 28% 34%, 42% 62%, 60% 22%, 100% 100%);
        opacity: 0.7;
      }

      .fp-skyline::before {
        left: 0;
      }

      .fp-skyline::after {
        right: 0;
        transform: scaleX(-1);
      }

      .fp-house-title {
        position: absolute;
        top: 4%;
        left: 50%;
        z-index: 4;
        transform: translateX(-50%);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        color: #f5f7fa;
        text-align: center;
        pointer-events: none;
        text-shadow: 0 3px 14px rgba(0, 0, 0, 0.7);
      }

      .fp-house-title strong {
        font-size: clamp(1rem, 2.1vw, 1.8rem);
        letter-spacing: 0;
        text-transform: uppercase;
      }

      .fp-title-small {
        color: #35c9ff;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
      }

      .fp-roof {
        position: absolute;
        top: 13%;
        left: 6%;
        right: 6%;
        height: 18%;
        z-index: 3;
        pointer-events: none;
        background:
          linear-gradient(180deg, rgba(255, 255, 255, 0.11), transparent 24%),
          linear-gradient(135deg, #38404b 0%, #1f2731 45%, #111820 100%);
        clip-path: polygon(50% 0, 100% 82%, 96% 100%, 50% 26%, 4% 100%, 0 82%);
        filter: drop-shadow(0 10px 18px rgba(0, 0, 0, 0.45));
      }

      .fp-roof-ridge {
        position: absolute;
        left: 10%;
        right: 10%;
        top: 69%;
        height: 4px;
        background: rgba(175, 191, 205, 0.55);
        transform: skewY(-7deg);
      }

      .fp-chimney {
        position: absolute;
        left: 17%;
        top: 16%;
        width: 30px;
        height: 56px;
        border-radius: 4px 4px 0 0;
        background: linear-gradient(90deg, #424a55, #222b34);
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
      }

      .fp-dish {
        position: absolute;
        right: 13%;
        top: 24%;
        width: 34px;
        height: 22px;
        border: 4px solid rgba(151, 174, 191, 0.7);
        border-top-color: transparent;
        border-left-color: transparent;
        border-radius: 50%;
        transform: rotate(-18deg);
      }

      .fp-dish::after {
        content: '';
        position: absolute;
        right: -12px;
        bottom: -17px;
        width: 3px;
        height: 24px;
        background: rgba(151, 174, 191, 0.6);
        transform: rotate(20deg);
      }

      .fp-house-shell {
        position: absolute;
        left: 8%;
        right: 8%;
        top: 24%;
        bottom: 10%;
        z-index: 5;
        background: linear-gradient(180deg, rgba(76, 90, 104, 0.16), rgba(15, 22, 30, 0.9));
        border: 6px solid #3c4855;
        border-bottom-width: 9px;
        box-shadow:
          inset 0 0 0 2px rgba(255, 255, 255, 0.04),
          0 24px 34px rgba(0, 0, 0, 0.48);
        pointer-events: none;
      }

      .fp-house-shell::before {
        content: '';
        position: absolute;
        left: -12px;
        right: -12px;
        top: 41.8%;
        height: 8px;
        z-index: 7;
        background: linear-gradient(90deg, #65717b, #2f3b47 18%, #596977 50%, #2f3b47 82%, #65717b);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.32);
      }

      .fp-room-layer {
        position: absolute;
        inset: 0;
        pointer-events: none;
      }

      .fp-foundation {
        position: absolute;
        left: 6.5%;
        right: 6.5%;
        bottom: 6.5%;
        height: 4%;
        z-index: 4;
        border-radius: 0 0 10px 10px;
        background:
          linear-gradient(180deg, #59636f, #232d36 54%, #101820);
        box-shadow: 0 12px 25px rgba(0, 0, 0, 0.45);
        pointer-events: none;
      }

      .fp-room {
        position: absolute;
        border: 3px solid #33404c;
        border-radius: 0;
        background: var(--room-base);
        cursor: pointer;
        transition: background-color 0.5s ease, box-shadow 0.3s ease, opacity 0.5s ease;
        overflow: hidden;
        pointer-events: auto;
        box-shadow:
          inset 0 0 0 1px rgba(255, 255, 255, 0.04),
          inset 0 18px 40px rgba(255, 255, 255, 0.03),
          inset 0 -24px 35px rgba(0, 0, 0, 0.2);
      }

      .fp-room:hover {
        border-color: rgba(89, 195, 255, 0.65);
        box-shadow:
          inset 0 0 30px rgba(0, 202, 255, 0.08),
          0 0 0 1px rgba(0, 202, 255, 0.18);
      }

      .fp-room-backwall {
        position: absolute;
        inset: 0 0 33%;
        z-index: 0;
        background:
          linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent 34%),
          radial-gradient(circle at 18% 26%, rgba(255, 241, 178, 0.08), transparent 20%),
          var(--room-base);
      }

      .fp-room-floor {
        position: absolute;
        left: -2%;
        right: -2%;
        bottom: -1%;
        height: 39%;
        z-index: 0;
        background:
          repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.035) 0 1px, transparent 1px 22px),
          linear-gradient(160deg, rgba(181, 129, 78, 0.24), rgba(68, 46, 38, 0.2));
        clip-path: polygon(0 26%, 100% 2%, 100% 100%, 0 100%);
        border-top: 1px solid rgba(255, 255, 255, 0.09);
        pointer-events: none;
      }

      .fp-room-decor {
        position: absolute;
        inset: 0;
        z-index: 1;
        pointer-events: none;
      }

      .fp-prop {
        position: absolute;
        display: block;
        border-radius: 5px;
        opacity: 0.92;
        filter: drop-shadow(0 5px 7px rgba(0, 0, 0, 0.28));
      }

      .fp-prop-window {
        background:
          linear-gradient(90deg, transparent calc(50% - 1px), rgba(240, 251, 255, 0.65) calc(50% - 1px) calc(50% + 1px), transparent calc(50% + 1px)),
          linear-gradient(0deg, transparent calc(50% - 1px), rgba(240, 251, 255, 0.55) calc(50% - 1px) calc(50% + 1px), transparent calc(50% + 1px)),
          linear-gradient(135deg, rgba(58, 205, 255, 0.28), rgba(255, 244, 196, 0.1));
        border: 2px solid rgba(214, 237, 246, 0.36);
        box-shadow: inset 0 0 14px rgba(109, 224, 255, 0.12);
      }

      .fp-prop-bed {
        border-radius: 8px 8px 5px 5px;
        background:
          linear-gradient(90deg, rgba(255, 255, 255, 0.55) 0 28%, transparent 29%),
          linear-gradient(180deg, #8e7968, #4a342d);
        border: 1px solid rgba(255, 255, 255, 0.15);
      }

      .fp-prop-bed::after,
      .fp-prop-bunk-bed::after {
        content: '';
        position: absolute;
        left: 8%;
        right: 8%;
        bottom: -18%;
        height: 24%;
        border-radius: 0 0 5px 5px;
        background: #221b1c;
      }

      .fp-prop-side-table,
      .fp-prop-coffee-table {
        background: linear-gradient(180deg, #956a3f, #3f2c22);
        border: 1px solid rgba(255, 255, 255, 0.12);
      }

      .fp-prop-lamp {
        border-radius: 50% 50% 5px 5px;
        background:
          linear-gradient(180deg, rgba(255, 242, 174, 0.95) 0 40%, transparent 41%),
          linear-gradient(90deg, transparent 42%, #8d9ba7 42% 58%, transparent 58%);
        box-shadow: 0 0 22px rgba(255, 217, 110, 0.2);
      }

      .fp-prop-picture {
        background:
          radial-gradient(circle at 65% 32%, #f1d37c 0 12%, transparent 13%),
          linear-gradient(145deg, #224b62, #15202b);
        border: 3px solid rgba(189, 144, 87, 0.74);
      }

      .fp-prop-bookshelf,
      .fp-prop-toy-shelf,
      .fp-prop-cabinet {
        background:
          repeating-linear-gradient(0deg, transparent 0 24%, rgba(255, 255, 255, 0.12) 25% 27%, transparent 28% 50%),
          repeating-linear-gradient(90deg, transparent 0 30%, rgba(0, 0, 0, 0.18) 31% 33%, transparent 34% 66%),
          linear-gradient(180deg, #8a633b, #3d2a1e);
        border: 1px solid rgba(255, 255, 255, 0.12);
      }

      .fp-prop-desk,
      .fp-prop-counter {
        background: linear-gradient(180deg, #a26c37 0 32%, #473225 33% 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
      }

      .fp-prop-chair {
        border-radius: 7px 7px 3px 3px;
        background:
          linear-gradient(90deg, transparent 0 18%, #263241 19% 80%, transparent 81%),
          linear-gradient(180deg, #6887a0, #233443);
      }

      .fp-prop-plant {
        border-radius: 50% 50% 6px 6px;
        background:
          radial-gradient(circle at 30% 26%, #78d68f 0 18%, transparent 19%),
          radial-gradient(circle at 66% 28%, #5ecb7b 0 20%, transparent 21%),
          radial-gradient(circle at 52% 13%, #8de4a1 0 17%, transparent 18%),
          linear-gradient(180deg, transparent 0 58%, #6f4930 59% 100%);
      }

      .fp-prop-stove {
        background:
          radial-gradient(circle at 30% 36%, rgba(0, 202, 255, 0.65) 0 12%, transparent 13%),
          radial-gradient(circle at 70% 36%, rgba(0, 202, 255, 0.65) 0 12%, transparent 13%),
          linear-gradient(180deg, #222c34, #0f151b);
        border: 1px solid rgba(180, 199, 210, 0.24);
      }

      .fp-prop-sink,
      .fp-prop-sink-basin {
        border-radius: 999px;
        background:
          radial-gradient(ellipse at center, rgba(182, 234, 248, 0.75) 0 35%, rgba(41, 72, 84, 0.9) 36% 62%, transparent 63%),
          linear-gradient(180deg, #778692, #28343d);
      }

      .fp-prop-tv-unit {
        background:
          linear-gradient(180deg, #111820 0 65%, #67452d 66% 100%);
        border: 1px solid rgba(160, 180, 191, 0.18);
      }

      .fp-prop-tv-unit::before {
        content: '';
        position: absolute;
        left: 8%;
        right: 8%;
        top: 8%;
        height: 54%;
        border-radius: 3px;
        background: linear-gradient(145deg, #0b1117, #2c4655);
        border: 1px solid rgba(0, 202, 255, 0.18);
      }

      .fp-prop-sofa {
        border-radius: 12px 12px 5px 5px;
        background:
          linear-gradient(90deg, rgba(255,255,255,0.11) 0 1px, transparent 1px 33%, rgba(255,255,255,0.11) 33% calc(33% + 1px), transparent calc(33% + 1px) 66%, rgba(255,255,255,0.11) 66% calc(66% + 1px), transparent calc(66% + 1px)),
          linear-gradient(180deg, #56677a, #263445);
        border: 1px solid rgba(255, 255, 255, 0.12);
      }

      .fp-prop-vent {
        background:
          repeating-linear-gradient(90deg, rgba(210, 230, 240, 0.5) 0 2px, transparent 2px 6px),
          rgba(50, 70, 78, 0.6);
        border: 1px solid rgba(210, 230, 240, 0.22);
      }

      .fp-prop-geyser-tank {
        border-radius: 12px;
        background:
          radial-gradient(circle at 50% 22%, rgba(255,255,255,0.75) 0 7%, transparent 8%),
          linear-gradient(180deg, #e2e4de, #8b958e);
        border: 2px solid rgba(255, 255, 255, 0.28);
      }

      .fp-prop-shower {
        background:
          linear-gradient(90deg, transparent 42%, #94a7af 43% 56%, transparent 57%),
          radial-gradient(ellipse at 50% 8%, #9caeb6 0 20%, transparent 21%);
      }

      .fp-prop-bunk-bed {
        border-radius: 6px;
        background:
          linear-gradient(180deg, #96734f 0 16%, transparent 17% 47%, #96734f 48% 64%, transparent 65%),
          linear-gradient(90deg, #60412e 0 11%, transparent 12% 88%, #60412e 89% 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
      }

      .fp-prop-rug {
        border-radius: 50%;
        background:
          radial-gradient(ellipse at center, rgba(255, 214, 114, 0.34) 0 45%, rgba(16, 122, 154, 0.36) 46% 100%);
      }

      .fp-prop-railing {
        background:
          repeating-linear-gradient(90deg, rgba(220, 235, 240, 0.55) 0 3px, transparent 3px 13px),
          linear-gradient(180deg, transparent 0 40%, rgba(220, 235, 240, 0.5) 41% 55%, transparent 56%);
      }

      .fp-prop-water-tank {
        border-radius: 999px 999px 8px 8px;
        background:
          linear-gradient(180deg, rgba(255,255,255,0.18), transparent 22%),
          linear-gradient(90deg, #29363d, #11191e 50%, #2f3e47);
        border: 2px solid rgba(158, 180, 190, 0.22);
      }

      .fp-room-label {
        position: absolute;
        bottom: 8px;
        left: 10px;
        z-index: 6;
        max-width: calc(100% - 18px);
        padding: 0.24rem 0.5rem;
        border-radius: 5px;
        background: linear-gradient(180deg, rgba(0, 146, 255, 0.88), rgba(0, 95, 166, 0.86));
        border: 1px solid rgba(165, 226, 255, 0.35);
        color: #f8fbff;
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0;
        pointer-events: none;
        font-weight: 800;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.32);
      }

      .fp-device {
        position: absolute;
        transform: translate(-50%, -50%);
        z-index: 9;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.25rem;
        min-width: 50px;
        max-width: 78px;
        min-height: 26px;
        padding: 0.2rem 0.35rem;
        border: 1px solid rgba(0, 202, 255, 0.32);
        border-radius: 6px;
        background: rgba(4, 10, 16, 0.9);
        color: #e6edf3;
        font: inherit;
        cursor: pointer;
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.32);
        transition: transform 0.2s ease, filter 0.3s ease, border-color 0.2s ease, background 0.2s ease, opacity 0.2s ease;
      }

      .fp-device-icon {
        font-size: 0.9rem;
        display: block;
        text-align: center;
        filter: drop-shadow(0 0 2px rgba(0, 202, 255, 0.3));
      }

      .fp-device-label {
        display: block;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.58rem;
        font-weight: 600;
        line-height: 1;
      }

      .fp-device:hover,
      .fp-device:focus-visible,
      .fp-device.selected {
        border-color: rgba(0, 202, 255, 0.8);
        background: rgba(0, 202, 255, 0.14);
        outline: none;
        transform: translate(-50%, -50%) scale(1.05);
      }

      .fp-device.is-off {
        opacity: 0.58;
        filter: grayscale(0.6);
      }

      .fp-device.device-highlight {
        animation: device-pulse 0.5s ease-in-out 4;
      }

      .fp-device.inverter-active .fp-device-icon {
        filter: drop-shadow(0 0 8px #00ff88) drop-shadow(0 0 16px #00ff88);
      }

      @keyframes device-pulse {
        0%, 100% { transform: translate(-50%, -50%) scale(1); filter: none; }
        50% { transform: translate(-50%, -50%) scale(1.4); filter: drop-shadow(0 0 10px rgba(0, 202, 255, 0.8)); }
      }

      .fp-avatar {
        position: absolute;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        transform: translate(-50%, -50%);
        z-index: 6;
        border: 2px solid rgba(255, 255, 255, 0.85);
        transition: left 0.8s ease, top 0.8s ease;
        pointer-events: auto;
        cursor: pointer;
        box-shadow: 0 2px 6px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.6rem;
        font-weight: 700;
        color: rgba(0, 0, 0, 0.75);
        font-family: var(--font-family, 'Inter', sans-serif);
        user-select: none;
      }

      .fp-avatar:hover {
        z-index: 12;
        transform: translate(-50%, -50%) scale(1.2);
      }

      .fp-avatar:hover::after {
        content: attr(title);
        position: absolute;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(13, 17, 23, 0.95);
        color: #e6edf3;
        padding: 3px 9px;
        border-radius: 5px;
        font-size: 0.65rem;
        font-weight: 500;
        white-space: nowrap;
        pointer-events: none;
        border: 1px solid rgba(0, 202, 255, 0.25);
        z-index: 12;
      }

      .fp-legend {
        position: absolute;
        left: 50%;
        bottom: 0.4%;
        transform: translateX(-50%);
        z-index: 9;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.3rem 0.75rem;
        background: rgba(13, 17, 23, 0.7);
        border: 1px solid rgba(0, 202, 255, 0.15);
        border-radius: 999px;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        flex-wrap: wrap;
        justify-content: center;
        max-width: 90%;
      }

      .fp-legend-title {
        font-size: 0.6rem;
        font-weight: 700;
        color: var(--color-text-muted, #8b949e);
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }

      .fp-legend-item {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        font-size: 0.62rem;
        color: var(--color-text, #e6edf3);
      }

      .fp-legend-dot {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 15px;
        height: 15px;
        border-radius: 50%;
        font-size: 0.5rem;
        font-weight: 700;
        color: rgba(0, 0, 0, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.7);
      }

      .fp-speech-bubble {
        position: absolute;
        bottom: 110%;
        left: 50%;
        transform: translateX(-50%) translateY(10px);
        background: rgba(13, 17, 23, 0.95);
        border: 1px solid rgba(0, 202, 255, 0.3);
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 0.65rem;
        color: #e6edf3;
        max-width: 220px;
        width: max-content;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.3s ease, transform 0.3s ease;
        z-index: 10;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        line-height: 1.4;
      }

      .fp-speech-bubble.visible {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
      }

      .fp-speech-bubble::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 5px solid transparent;
        border-top-color: rgba(0, 202, 255, 0.3);
      }

      .room-highlight {
        box-shadow: inset 0 0 30px rgba(0, 202, 255, 0.15), 0 0 15px rgba(0, 202, 255, 0.2) !important;
        border-color: rgba(0, 202, 255, 0.5) !important;
      }

      .room-dimmed {
        opacity: 0.25 !important;
        filter: grayscale(0.6);
      }

      .room-powered {
        box-shadow: inset 0 0 20px rgba(0, 255, 136, 0.1), 0 0 10px rgba(0, 255, 136, 0.15);
        border-color: rgba(0, 255, 136, 0.4) !important;
      }

      .fp-room-info {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        padding: 16px 20px;
        border-radius: 8px;
        z-index: 40;
        width: min(320px, calc(100% - 32px));
        background: rgba(13, 17, 23, 0.95);
        border: 1px solid rgba(0, 202, 255, 0.25);
        backdrop-filter: blur(12px);
        animation: fadeIn 0.2s ease;
      }

      .fp-room-info h3 {
        margin: 0 0 8px 0;
        font-size: 0.9rem;
        color: #00CAFF;
      }

      .fp-room-info-section {
        margin-bottom: 6px;
        font-size: 0.75rem;
        color: #8b949e;
      }

      .fp-room-info-section strong {
        display: block;
        margin-bottom: 6px;
        color: #e6edf3;
      }

      .fp-room-info-devices {
        display: grid;
        gap: 6px;
      }

      .fp-component-row {
        display: grid;
        grid-template-columns: 1.4rem minmax(0, 1fr) auto;
        align-items: center;
        gap: 0.45rem;
        width: 100%;
        min-height: 32px;
        padding: 0.35rem 0.45rem;
        border: 1px solid rgba(0, 202, 255, 0.14);
        border-radius: 6px;
        background: rgba(0, 202, 255, 0.06);
        color: #e6edf3;
        font: inherit;
        text-align: left;
        cursor: pointer;
      }

      .fp-component-row:hover,
      .fp-component-row:focus-visible {
        border-color: rgba(0, 202, 255, 0.5);
        background: rgba(0, 202, 255, 0.12);
        outline: none;
      }

      .fp-component-row-label {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.76rem;
        font-weight: 600;
      }

      .fp-component-row-status,
      .fp-empty {
        font-size: 0.68rem;
        color: #8b949e;
      }

      .fp-component-info {
        position: absolute;
        top: 16px;
        right: 16px;
        width: min(280px, calc(100% - 32px));
        padding: 16px;
        border-radius: 8px;
        z-index: 40;
        background: rgba(13, 17, 23, 0.95);
        border: 1px solid rgba(0, 202, 255, 0.25);
        backdrop-filter: blur(12px);
        animation: fadeInSide 0.2s ease;
      }

      .fp-component-info-heading {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 12px;
      }

      .fp-component-info-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 8px;
        background: rgba(0, 202, 255, 0.1);
        border: 1px solid rgba(0, 202, 255, 0.22);
        font-size: 1.2rem;
      }

      .fp-component-info h3 {
        margin: 0;
        font-size: 0.95rem;
        color: #00CAFF;
      }

      .fp-component-info p {
        margin: 2px 0 0;
        font-size: 0.72rem;
        color: #8b949e;
        line-height: 1.3;
      }

      .fp-component-status {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        padding: 0.55rem 0.65rem;
        margin-bottom: 12px;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.04);
        color: #8b949e;
        font-size: 0.74rem;
      }

      .fp-component-status strong {
        color: #e6edf3;
      }

      .fp-component-actions {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }

      .fp-component-action {
        min-height: 34px;
        border: 1px solid rgba(0, 202, 255, 0.22);
        border-radius: 6px;
        background: rgba(0, 202, 255, 0.08);
        color: #e6edf3;
        font: inherit;
        font-size: 0.75rem;
        font-weight: 600;
        cursor: pointer;
      }

      .fp-component-action:hover,
      .fp-component-action:focus-visible {
        border-color: rgba(0, 202, 255, 0.65);
        background: rgba(0, 202, 255, 0.16);
        outline: none;
      }

      .fp-room-info-close {
        position: absolute;
        top: 8px;
        right: 10px;
        background: none;
        border: none;
        color: #8b949e;
        cursor: pointer;
        font-size: 0.9rem;
        padding: 0;
      }

      .fp-room-info-close:hover {
        color: #e6edf3;
      }

      @keyframes fadeIn {
        from { opacity: 0; transform: translate(-50%, -50%) scale(0.95); }
        to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
      }

      @keyframes fadeInSide {
        from { opacity: 0; transform: translateY(-6px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
    document.head.appendChild(style);
  }
}

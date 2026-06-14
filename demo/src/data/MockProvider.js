/**
 * @file MockProvider - Built-in mock data that mirrors the backend REST API structure.
 * Provides offline-first data for the 3D demo without requiring a running backend.
 *
 * @typedef {import('./schemas.js').Device} Device
 * @typedef {import('./schemas.js').DevicesResponse} DevicesResponse
 * @typedef {import('./schemas.js').CommandResponse} CommandResponse
 * @typedef {import('./schemas.js').ContextSnapshot} ContextSnapshot
 * @typedef {import('./schemas.js').PatternsResponse} PatternsResponse
 * @typedef {import('./schemas.js').TiersResponse} TiersResponse
 * @typedef {import('./schemas.js').TierUpdateResponse} TierUpdateResponse
 */

export class MockProvider {
  constructor() {
    /** @type {Device[]} */
    this.devices = [
      {
        id: 'living_room_ac',
        name: 'Living Room AC',
        category: 'climate',
        room: 'livingRoom',
        brand: 'Daikin',
        state: { power: 'off', temperature: 24, mode: 'cool' },
      },
      {
        id: 'smart_lights',
        name: 'Smart Lights',
        category: 'lighting',
        room: 'all',
        brand: 'Philips Hue',
        state: { power: 'on', brightness: 80, colorTemp: 3000 },
      },
      {
        id: 'security_camera',
        name: 'Security Camera',
        category: 'security',
        room: 'balcony',
        brand: 'Ring',
        state: { power: 'on', recording: true, motionDetected: false },
      },
      {
        id: 'smart_lock',
        name: 'Smart Lock',
        category: 'security',
        room: 'balcony',
        brand: 'Yale',
        state: { locked: true, battery: 85 },
      },
      {
        id: 'kitchen_hub',
        name: 'Kitchen Appliance Hub',
        category: 'kitchen',
        room: 'kitchen',
        brand: 'Samsung',
        state: { power: 'on', activeAppliance: null },
      },
      {
        id: 'water_purifier',
        name: 'Water Purifier',
        category: 'utility',
        room: 'kitchen',
        brand: 'Kent',
        state: { power: 'on', filterLife: 72, waterLevel: 'full' },
      },
      {
        id: 'smart_geyser',
        name: 'Smart Geyser',
        category: 'utility',
        room: 'bath',
        brand: 'Havells',
        state: { power: 'off', temperature: 45, targetTemp: 55 },
      },
      {
        id: 'inverter_ups',
        name: 'Inverter/UPS',
        category: 'power',
        room: 'utility',
        brand: 'Luminous',
        state: { mode: 'standby', charge: 100, load: 0 },
      },
      {
        id: 'smart_tv',
        name: 'Smart TV',
        category: 'entertainment',
        room: 'livingRoom',
        brand: 'Fire TV',
        state: { power: 'off', input: 'hdmi1' },
      },
      {
        id: 'echo_devices',
        name: 'Echo Devices',
        category: 'assistant',
        room: 'livingRoom',
        brand: 'Amazon',
        state: { online: true, volume: 5 },
      },
    ];
  }

  /**
   * Get all registered devices with their current state.
   * Mirrors: GET /api/v1/devices
   * @returns {Promise<DevicesResponse>}
   */
  async getDevices() {
    return { devices: this.devices, count: this.devices.length };
  }

  /**
   * Get the current state of a specific device.
   * Mirrors: GET /api/v1/devices/{id}/state
   * @param {string} id - Device identifier
   * @returns {Promise<Device|null>}
   */
  async getDeviceState(id) {
    const device = this.devices.find((d) => d.id === id);
    return device ? { ...device } : null;
  }

  /**
   * Send a command to a device.
   * Mirrors: POST /api/v1/devices/{id}/command
   * @param {string} id - Device identifier
   * @param {Object} command - Command payload
   * @returns {Promise<CommandResponse>}
   */
  async sendCommand(id, command) {
    return {
      success: true,
      deviceId: id,
      command,
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Get the current unified home context snapshot.
   * Mirrors: GET /api/v1/context/snapshot
   * @returns {Promise<ContextSnapshot>}
   */
  async getContextSnapshot() {
    return {
      timestamp: new Date().toISOString(),
      deviceStates: this.devices.map((d) => ({ id: d.id, state: d.state })),
      activeActivities: [],
      environmentals: { temperature: 34, humidity: 65, powerGrid: 'stable' },
    };
  }

  /**
   * Get detected temporal patterns.
   * Mirrors: GET /api/v1/context/patterns
   * @returns {Promise<PatternsResponse>}
   */
  async getPatterns() {
    return {
      patterns: [
        {
          id: 'morning_routine',
          confidence: 0.92,
          schedule: '07:00',
          actions: ['geyser_preheat', 'lights_warm'],
        },
        {
          id: 'evening_cooling',
          confidence: 0.88,
          schedule: '17:30',
          actions: ['ac_precool'],
        },
        {
          id: 'security_away',
          confidence: 0.95,
          schedule: '09:00',
          actions: ['lock_arm', 'camera_alert'],
        },
      ],
    };
  }

  /**
   * Get current autonomy tier configuration for all device categories.
   * Mirrors: GET /api/v1/autonomy/tiers
   * @returns {Promise<TiersResponse>}
   */
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

  /**
   * Update autonomy tier for a device category.
   * Mirrors: PUT /api/v1/autonomy/tiers/{device}
   * @param {string} device - Device category name
   * @param {Object} config - Tier configuration to apply
   * @returns {Promise<TierUpdateResponse>}
   */
  async updateTier(device, config) {
    return { success: true, device, ...config };
  }
}

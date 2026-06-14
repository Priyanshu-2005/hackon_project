/**
 * ApiProvider - HTTP client for the real backend at localhost:8080.
 * Implements the same interface as MockProvider so DataLayer can
 * delegate calls transparently.
 */
export class ApiProvider {
  /**
   * @param {string} baseUrl - Backend base URL (default: http://localhost:8080)
   */
  constructor(baseUrl = 'http://localhost:8080') {
    this.baseUrl = baseUrl;
  }

  /**
   * Private helper that handles all HTTP communication.
   * @param {string} method - HTTP method (GET, POST, PUT)
   * @param {string} path - API path (e.g. /api/v1/devices)
   * @param {object|null} body - Request body for POST/PUT requests
   * @returns {Promise<object>} Parsed JSON response
   * @throws {Error} When the response status is not ok
   */
  async request(method, path, body = null) {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) {
      options.body = JSON.stringify(body);
    }
    const response = await fetch(`${this.baseUrl}${path}`, options);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json();
  }

  /**
   * Fetch all registered devices.
   * @returns {Promise<{devices: Array, count: number}>}
   */
  async getDevices() {
    return this.request('GET', '/api/v1/devices');
  }

  /**
   * Fetch current state of a specific device.
   * @param {string} id - Device identifier
   * @returns {Promise<object>}
   */
  async getDeviceState(id) {
    return this.request('GET', `/api/v1/devices/${id}/state`);
  }

  /**
   * Send a command to a specific device.
   * @param {string} id - Device identifier
   * @param {object} command - Command payload
   * @returns {Promise<object>}
   */
  async sendCommand(id, command) {
    return this.request('POST', `/api/v1/devices/${id}/command`, command);
  }

  /**
   * Fetch the current unified home context snapshot.
   * @returns {Promise<object>}
   */
  async getContextSnapshot() {
    return this.request('GET', '/api/v1/context/snapshot');
  }

  /**
   * Fetch detected temporal patterns.
   * @returns {Promise<{patterns: Array}>}
   */
  async getPatterns() {
    return this.request('GET', '/api/v1/context/patterns');
  }

  /**
   * Fetch autonomy tier configuration for all device categories.
   * @returns {Promise<{tiers: Array}>}
   */
  async getAutonomyTiers() {
    return this.request('GET', '/api/v1/autonomy/tiers');
  }

  /**
   * Update autonomy tier configuration for a specific device category.
   * @param {string} device - Device category identifier
   * @param {object} config - New tier configuration
   * @returns {Promise<object>}
   */
  async updateTier(device, config) {
    return this.request('PUT', `/api/v1/autonomy/tiers/${device}`, config);
  }
}

/**
 * Read a Vite env var when running in a bundled context. Falls back to the
 * provided default in tests / non-Vite environments where import.meta.env
 * is undefined.
 */
function envValue(key, fallback) {
  try {
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env[key]) {
      return import.meta.env[key];
    }
  } catch (_) {
    // import.meta not available (e.g. CommonJS test runner) — use fallback.
  }
  return fallback;
}

/**
 * ApiProvider - HTTP client for the real backend.
 *
 * Local demo (default):   baseUrl http://localhost:8080, prefix /api/v1
 * AWS API Gateway:        set VITE_API_BASE_URL to the stage URL
 *                         (e.g. https://abc123.execute-api.ap-south-1.amazonaws.com/dev)
 *                         and VITE_API_PREFIX to '' since the gateway routes
 *                         are mounted at the stage root (/devices, /context/...).
 * Optional auth:          set VITE_API_AUTH_TOKEN to send a Bearer token
 *                         (required when the API Gateway JWT authorizer is on).
 *
 * Implements the same interface as MockProvider so DataLayer can
 * delegate calls transparently.
 */
export class ApiProvider {
  /**
   * @param {string} [baseUrl] - Backend base URL. Defaults to VITE_API_BASE_URL
   *   or http://localhost:8080.
   * @param {object} [options]
   * @param {string} [options.apiPrefix] - Path prefix prepended to every route.
   *   Defaults to VITE_API_PREFIX or '/api/v1'. Use '' for API Gateway.
   * @param {string} [options.authToken] - Optional Bearer token. Defaults to
   *   VITE_API_AUTH_TOKEN.
   */
  constructor(baseUrl, options = {}) {
    this.baseUrl = baseUrl ?? envValue('VITE_API_BASE_URL', 'http://localhost:8080');
    this.apiPrefix = options.apiPrefix ?? envValue('VITE_API_PREFIX', '/api/v1');
    this.authToken = options.authToken ?? envValue('VITE_API_AUTH_TOKEN', null);
  }

  /**
   * Private helper that handles all HTTP communication.
   * @param {string} method - HTTP method (GET, POST, PUT)
   * @param {string} path - API path relative to the prefix (e.g. /devices)
   * @param {object|null} body - Request body for POST/PUT requests
   * @returns {Promise<object>} Parsed JSON response
   * @throws {Error} When the response status is not ok
   */
  async request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }
    const options = { method, headers };
    if (body) {
      options.body = JSON.stringify(body);
    }
    const response = await fetch(`${this.baseUrl}${this.apiPrefix}${path}`, options);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json();
  }

  /**
   * Fetch all registered devices.
   * Normalizes response to match MockProvider shape: {devices: [...], count: N}
   * @returns {Promise<{devices: Array, count: number}>}
   */
  async getDevices() {
    const data = await this.request('GET', '/devices');
    return {
      devices: data.devices ?? [],
      count: data.count ?? (data.devices?.length ?? 0),
    };
  }

  /**
   * Fetch current state of a specific device.
   * Returns the device entry object directly (matching MockProvider shape).
   * @param {string} id - Device identifier
   * @returns {Promise<object>}
   */
  async getDeviceState(id) {
    const data = await this.request('GET', `/devices/${id}/state`);
    // Backend returns the device entry object directly; pass through as-is
    return data;
  }

  /**
   * Send a command to a specific device.
   * @param {string} id - Device identifier
   * @param {object} command - Command payload
   * @returns {Promise<object>}
   */
  async sendCommand(id, command) {
    return this.request('POST', `/devices/${id}/command`, command);
  }

  /**
   * Fetch the current unified home context snapshot.
   * Normalizes response to match MockProvider shape:
   * {timestamp, deviceStates: [...], activeActivities: [...], environmentals: {...}}
   * @returns {Promise<object>}
   */
  async getContextSnapshot() {
    const data = await this.request('GET', '/context/snapshot');
    return {
      timestamp: data.timestamp,
      deviceStates: data.deviceStates ?? [],
      activeActivities: data.activeActivities ?? [],
      environmentals: data.environmentals ?? { temperature: 0, humidity: 0, powerGrid: 'unknown' },
    };
  }

  /**
   * Fetch detected temporal patterns.
   * Normalizes response to match MockProvider shape: {patterns: [...]}
   * @returns {Promise<{patterns: Array}>}
   */
  async getPatterns() {
    const data = await this.request('GET', '/context/patterns');
    return { patterns: data.patterns ?? [] };
  }

  /**
   * Fetch autonomy tier configuration for all device categories.
   * Normalizes response to match MockProvider shape: {tiers: [...]}
   * @returns {Promise<{tiers: Array}>}
   */
  async getAutonomyTiers() {
    const data = await this.request('GET', '/autonomy/tiers');
    return { tiers: data.tiers ?? [] };
  }

  /**
   * Update autonomy tier configuration for a specific device category.
   * @param {string} device - Device category identifier
   * @param {object} config - New tier configuration
   * @returns {Promise<object>}
   */
  async updateTier(device, config) {
    return this.request('PUT', `/autonomy/tiers/${device}`, config);
  }

  /**
   * Trigger the live power-cut scenario on the backend.
   * POST /api/v1/scenario/power-cut
   * @returns {Promise<{actions: Array, explanation: string, reasoning_chain: string}>}
   */
  async runPowerCutScenario() {
    return this.request('POST', '/scenario/power-cut', {});
  }
}

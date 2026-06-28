/**
 * DataLayer - Unified data access layer with mode toggle.
 * Delegates all calls to either MockProvider (offline) or ApiProvider (live backend).
 * Defaults to 'mock' mode on initialization.
 */
import { MockProvider } from './MockProvider.js';
import { ApiProvider } from './ApiProvider.js';

export class DataLayer {
  constructor() {
    /** @type {'mock' | 'real'} */
    this.mode = 'mock';
    this.mockProvider = new MockProvider();
    this.apiProvider = new ApiProvider();
  }

  /**
   * Returns the active provider based on the current mode.
   * @returns {MockProvider | ApiProvider}
   */
  get provider() {
    return this.mode === 'real' ? this.apiProvider : this.mockProvider;
  }

  /**
   * Switch between 'mock' and 'real' data modes.
   * @param {'mock' | 'real'} mode
   */
  setMode(mode) {
    this.mode = mode;
  }

  /**
   * Fetch all registered devices.
   * @returns {Promise<{devices: Array, count: number}>}
   */
  async getDevices() {
    return this.provider.getDevices();
  }

  /**
   * Fetch current state of a specific device.
   * @param {string} id - Device identifier
   * @returns {Promise<object>}
   */
  async getDeviceState(id) {
    return this.provider.getDeviceState(id);
  }

  /**
   * Send a command to a specific device.
   * @param {string} id - Device identifier
   * @param {object} command - Command payload
   * @returns {Promise<object>}
   */
  async sendCommand(id, command) {
    return this.provider.sendCommand(id, command);
  }

  /**
   * Fetch the current unified home context snapshot.
   * @returns {Promise<object>}
   */
  async getContextSnapshot() {
    return this.provider.getContextSnapshot();
  }

  /**
   * Fetch detected temporal patterns.
   * @returns {Promise<{patterns: Array}>}
   */
  async getPatterns() {
    return this.provider.getPatterns();
  }

  /**
   * Fetch autonomy tier configuration for all device categories.
   * @returns {Promise<{tiers: Array}>}
   */
  async getAutonomyTiers() {
    return this.provider.getAutonomyTiers();
  }

  /**
   * Update autonomy tier configuration for a specific device category.
   * @param {string} device - Device category identifier
   * @param {object} config - New tier configuration
   * @returns {Promise<object>}
   */
  async updateTier(device, config) {
    return this.provider.updateTier(device, config);
  }
}

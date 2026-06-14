/**
 * StateStore — Centralized state management for devices, family positions,
 * trust scores, and the event log.
 *
 * Uses a lightweight pub/sub pattern (Map<string, Set<Function>>) so that
 * UI panels and other modules can react to state changes without tight coupling.
 *
 * Requirements: 9.1, 9.2, 9.3
 */
export class StateStore {
  constructor() {
    /** @type {Map<string, { state: object, room: string, category: string, tier: number }>} */
    this.devices = new Map();

    /** @type {Map<string, { room: string, activity: string }>} */
    this.familyPositions = new Map();

    /** @type {Map<string, { score: number, tier: number }>} */
    this.trustScores = new Map();

    /** @type {Array<object>} Chronological event log entries */
    this.events = [];

    /** @type {Map<string, Set<Function>>} Pub/sub listeners */
    this.listeners = new Map();
  }

  /**
   * Merge state into the device entry and notify listeners.
   * @param {string} deviceId
   * @param {object} state — partial state to merge
   */
  setDeviceState(deviceId, state) {
    const existing = this.devices.get(deviceId) || {};
    this.devices.set(deviceId, { ...existing, ...state });
    this.emit('device:' + deviceId, state);
  }

  /**
   * Update a family member's current position and activity.
   * @param {string} memberId
   * @param {string} room
   * @param {string} activity
   */
  setFamilyPosition(memberId, room, activity) {
    this.familyPositions.set(memberId, { room, activity });
    this.emit('family:' + memberId, { room, activity });
  }

  /**
   * Adjust a category's trust score by delta (clamped 0–100) and recalculate tier.
   * @param {string} category
   * @param {number} delta — positive or negative adjustment
   */
  updateTrustScore(category, delta) {
    const current = this.trustScores.get(category) || { score: 0, tier: 1 };
    const newScore = Math.max(0, Math.min(100, current.score + delta));
    const tier = this.calculateTier(newScore);
    this.trustScores.set(category, { score: newScore, tier });
    this.emit('trust:' + category, { score: newScore, tier });
  }

  /**
   * Map a numeric score (0–100) to an autonomy tier (1–5).
   *   0–20  → Tier 1
   *   21–45 → Tier 2
   *   46–70 → Tier 3
   *   71–90 → Tier 4
   *   91–100 → Tier 5
   * @param {number} score
   * @returns {number} tier (1–5)
   */
  calculateTier(score) {
    if (score >= 91) return 5;
    if (score >= 71) return 4;
    if (score >= 46) return 3;
    if (score >= 21) return 2;
    return 1;
  }

  /**
   * Append an entry to the chronological event log and notify listeners.
   * @param {object} entry — event log entry (should contain action, device, reasoning, timestamp fields)
   */
  addEventLogEntry(entry) {
    this.events.push(entry);
    this.emit('eventlog', entry);
  }

  /**
   * Register a listener for a given state key.
   * @param {string} key — e.g. 'device:living_room_ac', 'trust:climate', 'eventlog'
   * @param {Function} callback — invoked with (data) when key is emitted
   */
  on(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    this.listeners.get(key).add(callback);
  }

  /**
   * Notify all listeners registered for a given key.
   * @param {string} key
   * @param {*} data — payload passed to each callback
   */
  emit(key, data) {
    const cbs = this.listeners.get(key);
    if (cbs) {
      cbs.forEach(cb => cb(data));
    }
  }
}

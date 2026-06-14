/**
 * Event names used throughout the application.
 */
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

/**
 * Simple pub/sub event bus for decoupled module communication.
 */
class EventBus {
  constructor() {
    /** @type {Map<string, Set<Function>>} */
    this.listeners = new Map();
  }

  /**
   * Subscribe to an event.
   * @param {string} event - Event name from EVENTS enum.
   * @param {Function} handler - Callback invoked when the event fires.
   */
  on(event, handler) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(handler);
  }

  /**
   * Unsubscribe from an event.
   * @param {string} event - Event name.
   * @param {Function} handler - Previously registered callback.
   */
  off(event, handler) {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Emit an event to all subscribers.
   * @param {string} event - Event name.
   * @param {*} payload - Data passed to each handler.
   */
  emit(event, payload) {
    const handlers = this.listeners.get(event);
    if (handlers) {
      for (const handler of handlers) {
        handler(payload);
      }
    }
  }
}

/** Singleton event bus instance shared across all modules. */
export const eventBus = new EventBus();

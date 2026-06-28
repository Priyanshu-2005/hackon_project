/**
 * EventScheduler — evaluates scheduled proactive actions against the
 * current simulation time and fires events when triggers are met.
 *
 * Registers itself on the SimulationEngine tick loop and checks each
 * action's triggerTime on every frame. Once fired, an action is not
 * repeated (one-shot per simulation run).
 *
 * Requirements: 8.1, 8.3, 9.2
 */
import { eventBus, EVENTS } from '../utils/eventBus.js';

export class EventScheduler {
  /**
   * @param {import('./SimulationEngine.js').SimulationEngine} simulationEngine
   * @param {import('./StateStore.js').StateStore} stateStore
   * @param {import('../utils/eventBus.js').eventBus} bus
   */
  constructor(simulationEngine, stateStore, bus = eventBus) {
    this.simulation = simulationEngine;
    this.store = stateStore;
    this.bus = bus;

    /** @type {Array<object>} Loaded proactive action definitions */
    this.scheduledActions = [];

    /** @type {Set<string>} IDs of actions already fired this run */
    this.firedActions = new Set();

    // Register on simulation tick
    this.simulation.onTick((time) => this.evaluate(time));
  }

  /**
   * Load a set of proactive actions into the scheduler.
   * Assigns unique IDs and clears the fired tracking set.
   * @param {Array<object>} actions — action definitions from ProactiveActions
   */
  loadActions(actions) {
    this.scheduledActions = actions.map((a) => ({
      ...a,
      id: a.id || ('act-' + Date.now() + '-' + Math.random().toString(36).slice(2)),
    }));
    this.firedActions.clear();
  }

  /**
   * Evaluate all scheduled actions against the current simulation time.
   * Fires each action at most once when currentTime >= triggerTime.
   * @param {number} currentTimeMinutes — simulation time in minutes (0–1439)
   */
  evaluate(currentTimeMinutes) {
    for (const action of this.scheduledActions) {
      if (this.firedActions.has(action.id)) continue;

      if (currentTimeMinutes >= action.triggerTime) {
        this.firedActions.add(action.id);

        // Emit proactive action event via eventBus
        this.bus.emit(EVENTS.PROACTIVE_ACTION, {
          ...action,
          timestamp: currentTimeMinutes,
        });

        // Add entry to the event log in StateStore
        this.store.addEventLogEntry({
          time: currentTimeMinutes,
          action: action.name,
          device: action.targetDevice,
          reasoning: action.reasoning,
          type: action.actionType,
        });

        // Increase trust score for the action's category (+3 per action)
        this.store.updateTrustScore(action.category, 3);
      }
    }
  }
}

/**
 * SimulationEngine — drives the 24-hour day simulation clock.
 *
 * Tracks simulated time in minutes (0–1439, representing 00:00 to 23:59),
 * advances via requestAnimationFrame, and notifies registered listeners
 * on every tick with the current simulated time.
 *
 * Requirements: 14.1, 14.2, 14.3, 14.4, 14.6
 */
export class SimulationEngine {
  constructor() {
    /** @type {number} Current simulation time in minutes since midnight (0–1439) */
    this.currentTimeMinutes = 0;

    /** @type {number} Speed multiplier — how fast simulation advances relative to real time.
     *  Default 60 means 1 real second = 1 simulated minute.
     *  Options: 1, 10, 60, 120 */
    this.speedMultiplier = 60;

    /** @type {boolean} Whether the tick loop is active */
    this.isRunning = false;

    /** @type {number|null} performance.now() timestamp of the last tick */
    this.lastRealTime = null;

    /** @type {Set<function(number): void>} Registered tick listener callbacks */
    this.listeners = new Set();

    /** @type {number|null} requestAnimationFrame handle for cancellation */
    this._rafId = null;
  }

  /**
   * Start the simulation from the beginning.
   * Sets isRunning to true, records the initial real timestamp,
   * and begins the tick loop.
   */
  start() {
    this.isRunning = true;
    this.lastRealTime = performance.now();
    this._scheduleTick();
  }

  /**
   * Pause the simulation. Stops the tick loop but preserves current time.
   */
  pause() {
    this.isRunning = false;
    if (this._rafId !== null) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  /**
   * Resume a paused simulation.
   * Resets lastRealTime to avoid a large time jump, then restarts the tick loop.
   */
  resume() {
    if (this.isRunning) return; // Already running
    this.isRunning = true;
    this.lastRealTime = performance.now();
    this._scheduleTick();
  }

  /**
   * Update the speed multiplier.
   * @param {number} multiplier — one of 1, 10, 60, 120
   */
  setSpeed(multiplier) {
    this.speedMultiplier = multiplier;
  }

  /**
   * Jump to a specific time in the simulation day.
   * Clamps to the valid range 0–1439 and notifies all listeners.
   * @param {number} timeMinutes — target time in minutes since midnight
   */
  seekTo(timeMinutes) {
    this.currentTimeMinutes = Math.max(0, Math.min(1439, timeMinutes));
    this.notifyListeners();
  }

  /**
   * Core tick function — called each animation frame.
   * Calculates real time elapsed since last frame, converts to simulated
   * minutes based on the speed multiplier, advances the clock, and notifies
   * listeners. Auto-pauses when the end of day (1439) is reached.
   */
  tick() {
    if (!this.isRunning) return;

    const now = performance.now();
    const realDeltaMs = now - this.lastRealTime;
    this.lastRealTime = now;

    // Convert real milliseconds to simulated minutes:
    // At speedMultiplier=60, 1 real second (1000ms) → 1 simulated minute
    // Formula: (realDeltaMs / 1000) gives real seconds elapsed,
    //          * (speedMultiplier / 60) converts to simulated minutes
    const simDeltaMinutes = (realDeltaMs / 1000) * (this.speedMultiplier / 60);
    this.currentTimeMinutes += simDeltaMinutes;

    // Cap at end of day and auto-pause
    if (this.currentTimeMinutes >= 1439) {
      this.currentTimeMinutes = 1439;
      this.isRunning = false;
    }

    this.notifyListeners();

    // Continue the loop if still running
    if (this.isRunning) {
      this._scheduleTick();
    }
  }

  /**
   * Register a callback to be called on every simulation tick.
   * @param {function(number): void} callback — receives currentTimeMinutes
   */
  onTick(callback) {
    this.listeners.add(callback);
  }

  /**
   * Unregister a previously registered tick callback.
   * @param {function(number): void} callback — the callback to remove
   */
  offTick(callback) {
    this.listeners.delete(callback);
  }

  /**
   * Notify all registered listeners with the current simulation time.
   */
  notifyListeners() {
    for (const cb of this.listeners) {
      cb(this.currentTimeMinutes);
    }
  }

  /**
   * Schedule the next tick via requestAnimationFrame.
   * @private
   */
  _scheduleTick() {
    this._rafId = requestAnimationFrame(() => this.tick());
  }
}

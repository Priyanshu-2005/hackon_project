import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { test as fcTest } from '@fast-check/vitest';
import fc from 'fast-check';
import { SimulationEngine } from './SimulationEngine.js';

// Provide browser-like globals for the test environment
globalThis.requestAnimationFrame = globalThis.requestAnimationFrame || ((cb) => setTimeout(cb, 16));
globalThis.cancelAnimationFrame = globalThis.cancelAnimationFrame || ((id) => clearTimeout(id));

describe('SimulationEngine', () => {
  let engine;

  beforeEach(() => {
    engine = new SimulationEngine();
    vi.useFakeTimers();
  });

  afterEach(() => {
    engine.pause();
    vi.useRealTimers();
  });

  describe('constructor', () => {
    it('initializes with correct default values', () => {
      expect(engine.currentTimeMinutes).toBe(0);
      expect(engine.speedMultiplier).toBe(60);
      expect(engine.isRunning).toBe(false);
      expect(engine.lastRealTime).toBeNull();
      expect(engine.listeners).toBeInstanceOf(Set);
      expect(engine.listeners.size).toBe(0);
    });
  });

  describe('start()', () => {
    it('sets isRunning to true', () => {
      engine.start();
      expect(engine.isRunning).toBe(true);
    });

    it('sets lastRealTime to current performance.now()', () => {
      const mockNow = 12345;
      vi.spyOn(performance, 'now').mockReturnValue(mockNow);
      engine.start();
      expect(engine.lastRealTime).toBe(mockNow);
    });

    it('schedules a requestAnimationFrame tick', () => {
      const rafSpy = vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
      engine.start();
      expect(rafSpy).toHaveBeenCalled();
      rafSpy.mockRestore();
    });
  });

  describe('pause()', () => {
    it('sets isRunning to false', () => {
      engine.isRunning = true;
      engine.pause();
      expect(engine.isRunning).toBe(false);
    });

    it('cancels pending animation frame', () => {
      const cancelSpy = vi.spyOn(globalThis, 'cancelAnimationFrame').mockImplementation(() => {});
      vi.spyOn(globalThis, 'requestAnimationFrame').mockReturnValue(42);
      engine.start();
      engine.pause();
      expect(cancelSpy).toHaveBeenCalledWith(42);
      cancelSpy.mockRestore();
    });
  });

  describe('resume()', () => {
    it('sets isRunning to true when paused', () => {
      engine.isRunning = false;
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
      engine.resume();
      expect(engine.isRunning).toBe(true);
    });

    it('resets lastRealTime to avoid large delta', () => {
      const mockNow = 99999;
      vi.spyOn(performance, 'now').mockReturnValue(mockNow);
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
      engine.resume();
      expect(engine.lastRealTime).toBe(mockNow);
    });

    it('does nothing if already running', () => {
      engine.isRunning = true;
      const rafSpy = vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
      engine.resume();
      expect(rafSpy).not.toHaveBeenCalled();
      rafSpy.mockRestore();
    });
  });

  describe('setSpeed()', () => {
    it('updates the speedMultiplier', () => {
      engine.setSpeed(120);
      expect(engine.speedMultiplier).toBe(120);
    });

    it('accepts all valid speed values', () => {
      for (const speed of [1, 10, 60, 120]) {
        engine.setSpeed(speed);
        expect(engine.speedMultiplier).toBe(speed);
      }
    });
  });

  describe('seekTo()', () => {
    it('sets currentTimeMinutes to the given value', () => {
      engine.seekTo(720);
      expect(engine.currentTimeMinutes).toBe(720);
    });

    it('clamps to 0 when given negative value', () => {
      engine.seekTo(-100);
      expect(engine.currentTimeMinutes).toBe(0);
    });

    it('clamps to 1439 when given value above max', () => {
      engine.seekTo(2000);
      expect(engine.currentTimeMinutes).toBe(1439);
    });

    it('notifies listeners after seeking', () => {
      const listener = vi.fn();
      engine.onTick(listener);
      engine.seekTo(600);
      expect(listener).toHaveBeenCalledWith(600);
    });
  });

  describe('tick()', () => {
    it('does nothing when isRunning is false', () => {
      engine.isRunning = false;
      const listener = vi.fn();
      engine.onTick(listener);
      engine.tick();
      expect(listener).not.toHaveBeenCalled();
    });

    it('advances time based on real delta and speed multiplier', () => {
      engine.isRunning = true;
      engine.speedMultiplier = 60;
      engine.lastRealTime = 0;

      // Simulate 1 real second elapsed (1000ms)
      vi.spyOn(performance, 'now').mockReturnValue(1000);
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);

      engine.tick();

      // At 60x speed: (1000/1000) * (60/60) = 1 simulated minute
      expect(engine.currentTimeMinutes).toBeCloseTo(1, 5);
    });

    it('advances faster at higher speed multipliers', () => {
      engine.isRunning = true;
      engine.speedMultiplier = 120;
      engine.lastRealTime = 0;

      vi.spyOn(performance, 'now').mockReturnValue(1000);
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);

      engine.tick();

      // At 120x speed: (1000/1000) * (120/60) = 2 simulated minutes
      expect(engine.currentTimeMinutes).toBeCloseTo(2, 5);
    });

    it('advances slower at 1x speed', () => {
      engine.isRunning = true;
      engine.speedMultiplier = 1;
      engine.lastRealTime = 0;

      vi.spyOn(performance, 'now').mockReturnValue(1000);
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);

      engine.tick();

      // At 1x speed: (1000/1000) * (1/60) = 1/60 simulated minutes
      expect(engine.currentTimeMinutes).toBeCloseTo(1 / 60, 5);
    });

    it('stops at 1439 (end of day) and sets isRunning to false', () => {
      engine.isRunning = true;
      engine.currentTimeMinutes = 1438.5;
      engine.speedMultiplier = 60;
      engine.lastRealTime = 0;

      // Large enough delta to push past 1439
      vi.spyOn(performance, 'now').mockReturnValue(2000);
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);

      engine.tick();

      expect(engine.currentTimeMinutes).toBe(1439);
      expect(engine.isRunning).toBe(false);
    });

    it('notifies listeners on each tick', () => {
      engine.isRunning = true;
      engine.lastRealTime = 0;
      const listener = vi.fn();
      engine.onTick(listener);

      vi.spyOn(performance, 'now').mockReturnValue(500);
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);

      engine.tick();

      expect(listener).toHaveBeenCalledTimes(1);
      expect(listener).toHaveBeenCalledWith(engine.currentTimeMinutes);
    });
  });

  describe('onTick() / offTick()', () => {
    it('registers a listener', () => {
      const cb = vi.fn();
      engine.onTick(cb);
      expect(engine.listeners.has(cb)).toBe(true);
    });

    it('removes a listener', () => {
      const cb = vi.fn();
      engine.onTick(cb);
      engine.offTick(cb);
      expect(engine.listeners.has(cb)).toBe(false);
    });

    it('removed listener does not get called', () => {
      const cb = vi.fn();
      engine.onTick(cb);
      engine.offTick(cb);
      engine.notifyListeners();
      expect(cb).not.toHaveBeenCalled();
    });
  });

  describe('notifyListeners()', () => {
    it('calls all registered listeners with currentTimeMinutes', () => {
      const cb1 = vi.fn();
      const cb2 = vi.fn();
      engine.onTick(cb1);
      engine.onTick(cb2);
      engine.currentTimeMinutes = 300;
      engine.notifyListeners();
      expect(cb1).toHaveBeenCalledWith(300);
      expect(cb2).toHaveBeenCalledWith(300);
    });

    it('does not fail when no listeners registered', () => {
      expect(() => engine.notifyListeners()).not.toThrow();
    });
  });
});


/**
 * Property-Based Tests for SimulationEngine
 *
 * Validates: Requirements 7.5, 7.6, 14.1–14.6
 */
describe('SimulationEngine - Property Tests', () => {
  // Provide browser-like globals for the property test environment
  beforeEach(() => {
    globalThis.requestAnimationFrame = globalThis.requestAnimationFrame || ((cb) => setTimeout(cb, 16));
    globalThis.cancelAnimationFrame = globalThis.cancelAnimationFrame || ((id) => clearTimeout(id));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Property 7: Speed multiplier clock advancement
   * Higher speed multipliers advance the clock faster.
   *
   * **Validates: Requirements 7.5**
   *
   * For any two speed multipliers where speedA < speedB, given the same
   * real-time delta, the engine with speedB advances more simulated minutes.
   */
  describe('Property 7: Speed multiplier clock advancement', () => {
    fcTest.prop(
      [
        fc.integer({ min: 1, max: 120 }),   // speedA
        fc.integer({ min: 1, max: 120 }),   // speedB
        fc.integer({ min: 16, max: 5000 }), // realDeltaMs
      ]
    )(
      'higher speed multipliers advance the clock faster',
      (speedA, speedB, realDeltaMs) => {
        // Ensure speedA < speedB
        const lowSpeed = Math.min(speedA, speedB);
        const highSpeed = Math.max(speedA, speedB);

        // Skip degenerate case where speeds are equal
        fc.pre(lowSpeed < highSpeed);

        // Engine with low speed
        const engineLow = new SimulationEngine();
        engineLow.isRunning = true;
        engineLow.lastRealTime = 0;
        engineLow.speedMultiplier = lowSpeed;

        vi.spyOn(performance, 'now').mockReturnValue(realDeltaMs);
        vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
        engineLow.tick();
        const advanceLow = engineLow.currentTimeMinutes;

        vi.restoreAllMocks();

        // Engine with high speed
        const engineHigh = new SimulationEngine();
        engineHigh.isRunning = true;
        engineHigh.lastRealTime = 0;
        engineHigh.speedMultiplier = highSpeed;

        vi.spyOn(performance, 'now').mockReturnValue(realDeltaMs);
        vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
        engineHigh.tick();
        const advanceHigh = engineHigh.currentTimeMinutes;

        vi.restoreAllMocks();

        // Higher speed should advance more (or equal if both cap at 1439)
        expect(advanceHigh).toBeGreaterThanOrEqual(advanceLow);
      }
    );

    fcTest.prop(
      [
        fc.constantFrom(1, 10, 60, 120),    // speedMultiplier
        fc.integer({ min: 100, max: 3000 }), // realDeltaMs
      ]
    )(
      'time advancement is proportional to speed multiplier',
      (speed, realDeltaMs) => {
        const engine = new SimulationEngine();
        engine.isRunning = true;
        engine.lastRealTime = 0;
        engine.speedMultiplier = speed;

        vi.spyOn(performance, 'now').mockReturnValue(realDeltaMs);
        vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
        engine.tick();

        const expectedAdvance = (realDeltaMs / 1000) * (speed / 60);
        // Capped at 1439
        const expectedClamped = Math.min(1439, expectedAdvance);

        expect(engine.currentTimeMinutes).toBeCloseTo(expectedClamped, 5);

        vi.restoreAllMocks();
      }
    );
  });

  /**
   * Property 8: Scrubber-simulation time bidirectional sync
   * seekTo sets the currentTimeMinutes correctly (clamped to 0-1439).
   *
   * **Validates: Requirements 7.6**
   *
   * For any seekTo value, the resulting currentTimeMinutes is clamped
   * to [0, 1439] and listeners are notified with the clamped value.
   */
  describe('Property 8: Scrubber-simulation time bidirectional sync', () => {
    fcTest.prop(
      [fc.integer({ min: 0, max: 1439 })]
    )(
      'seekTo(value) sets currentTimeMinutes to that value within valid range',
      (timeMinutes) => {
        const engine = new SimulationEngine();
        engine.seekTo(timeMinutes);
        expect(engine.currentTimeMinutes).toBe(timeMinutes);
      }
    );

    fcTest.prop(
      [fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true })]
    )(
      'seekTo clamps to 0-1439 range for any input',
      (value) => {
        const engine = new SimulationEngine();
        engine.seekTo(value);
        expect(engine.currentTimeMinutes).toBeGreaterThanOrEqual(0);
        expect(engine.currentTimeMinutes).toBeLessThanOrEqual(1439);
      }
    );

    fcTest.prop(
      [fc.double({ min: -1000, max: 3000, noNaN: true, noDefaultInfinity: true })]
    )(
      'seekTo notifies listeners with the clamped time value',
      (value) => {
        const engine = new SimulationEngine();
        const listener = vi.fn();
        engine.onTick(listener);

        engine.seekTo(value);

        const expected = Math.max(0, Math.min(1439, value));
        expect(listener).toHaveBeenCalledTimes(1);
        expect(listener).toHaveBeenCalledWith(expected);
      }
    );

    fcTest.prop(
      [fc.integer({ min: -5000, max: -1 })]
    )(
      'seekTo clamps negative values to 0',
      (negativeValue) => {
        const engine = new SimulationEngine();
        engine.seekTo(negativeValue);
        expect(engine.currentTimeMinutes).toBe(0);
      }
    );

    fcTest.prop(
      [fc.integer({ min: 1440, max: 10000 })]
    )(
      'seekTo clamps values above 1439 to 1439',
      (overflowValue) => {
        const engine = new SimulationEngine();
        engine.seekTo(overflowValue);
        expect(engine.currentTimeMinutes).toBe(1439);
      }
    );
  });

  /**
   * Property 9: Pause and resume controls clock
   * Paused engine doesn't advance, resumed engine does.
   *
   * **Validates: Requirements 14.1–14.6**
   *
   * When isRunning is false, calling tick() does NOT advance the clock.
   * When isRunning is true, calling tick() DOES advance the clock.
   */
  describe('Property 9: Pause and resume controls clock', () => {
    fcTest.prop(
      [
        fc.integer({ min: 0, max: 1400 }),    // initial time
        fc.integer({ min: 16, max: 5000 }),   // realDeltaMs
        fc.constantFrom(1, 10, 60, 120),      // speed
      ]
    )(
      'paused engine does not advance time on tick',
      (initialTime, realDeltaMs, speed) => {
        const engine = new SimulationEngine();
        engine.currentTimeMinutes = initialTime;
        engine.speedMultiplier = speed;
        engine.isRunning = false; // paused

        vi.spyOn(performance, 'now').mockReturnValue(realDeltaMs);
        engine.tick();

        // Time should not change
        expect(engine.currentTimeMinutes).toBe(initialTime);

        vi.restoreAllMocks();
      }
    );

    fcTest.prop(
      [
        fc.integer({ min: 0, max: 1400 }),    // initial time (below cap)
        fc.integer({ min: 100, max: 2000 }),  // realDeltaMs
        fc.constantFrom(1, 10, 60, 120),      // speed
      ]
    )(
      'resumed engine advances time on tick',
      (initialTime, realDeltaMs, speed) => {
        const engine = new SimulationEngine();
        engine.currentTimeMinutes = initialTime;
        engine.speedMultiplier = speed;
        engine.isRunning = true;
        engine.lastRealTime = 0;

        vi.spyOn(performance, 'now').mockReturnValue(realDeltaMs);
        vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
        engine.tick();

        // Time should have advanced (or capped at 1439)
        expect(engine.currentTimeMinutes).toBeGreaterThanOrEqual(initialTime);

        vi.restoreAllMocks();
      }
    );

    fcTest.prop(
      [fc.integer({ min: 0, max: 1439 })]
    )(
      'pause() sets isRunning to false for any state',
      (initialTime) => {
        const engine = new SimulationEngine();
        engine.currentTimeMinutes = initialTime;
        engine.isRunning = true;
        vi.spyOn(globalThis, 'cancelAnimationFrame').mockImplementation(() => {});

        engine.pause();

        expect(engine.isRunning).toBe(false);

        vi.restoreAllMocks();
      }
    );

    fcTest.prop(
      [fc.integer({ min: 0, max: 1439 })]
    )(
      'resume() sets isRunning to true when paused',
      (initialTime) => {
        const engine = new SimulationEngine();
        engine.currentTimeMinutes = initialTime;
        engine.isRunning = false;
        vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
        vi.spyOn(performance, 'now').mockReturnValue(1000);

        engine.resume();

        expect(engine.isRunning).toBe(true);

        vi.restoreAllMocks();
      }
    );

    fcTest.prop(
      [fc.integer({ min: 0, max: 1439 })]
    )(
      'start() sets isRunning to true',
      (initialTime) => {
        const engine = new SimulationEngine();
        engine.currentTimeMinutes = initialTime;
        engine.isRunning = false;
        vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
        vi.spyOn(performance, 'now').mockReturnValue(1000);

        engine.start();

        expect(engine.isRunning).toBe(true);

        vi.restoreAllMocks();
      }
    );
  });
});

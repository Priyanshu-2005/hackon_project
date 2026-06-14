// @vitest-environment happy-dom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fc from 'fast-check';
import { UIManager } from './UIManager.js';

/**
 * Property-Based Tests for UIManager phase navigation.
 *
 * **Validates: Requirements 3.4**
 *
 * Property 3: No backward phase navigation — once in deployment phase,
 * cannot go back to learning without page reload. For any sequence of
 * user interactions while in the Deployment Phase, the application phase
 * SHALL remain 'deployment' and SHALL NOT revert to 'learning' unless
 * an explicit page reload or reset action is triggered.
 */

function setupDOM() {
  document.body.innerHTML = `
    <div id="learning-phase" class="phase-panel"></div>
    <div id="deployment-phase" class="phase-panel hidden"></div>
    <button id="deploy-btn" class="btn-deploy">Deploy →</button>
  `;
}

function createMockSimulationEngine() {
  return {
    start: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    seekTo: vi.fn(),
    setSpeed: vi.fn(),
    onTick: vi.fn(),
    offTick: vi.fn(),
  };
}

function createMockStateStore() {
  return {
    devices: new Map(),
    trustScores: new Map(),
    events: [],
    on: vi.fn(),
    emit: vi.fn(),
  };
}

describe('UIManager Property Tests - Phase Navigation', () => {
  let uiManager;
  let mockSimulation;
  let mockStateStore;

  beforeEach(() => {
    setupDOM();
    mockSimulation = createMockSimulationEngine();
    mockStateStore = createMockStateStore();
    uiManager = new UIManager(mockStateStore, mockSimulation);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('Property 3: No backward phase navigation', () => {
    it('starting from learning, calling deploy() always transitions to deployment', () => {
      fc.assert(
        fc.property(
          fc.constant(null),
          () => {
            // Fresh instance starts in 'learning'
            setupDOM();
            const sim = createMockSimulationEngine();
            const store = createMockStateStore();
            const manager = new UIManager(store, sim);

            expect(manager.getCurrentPhase()).toBe('learning');
            manager.deploy();
            expect(manager.getCurrentPhase()).toBe('deployment');
          }
        ),
        { numRuns: 100 }
      );
    });

    it('once in deployment, calling deploy() any number of times never changes the phase', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 50 }),
          (numCalls) => {
            // Transition to deployment first
            setupDOM();
            const sim = createMockSimulationEngine();
            const store = createMockStateStore();
            const manager = new UIManager(store, sim);
            manager.deploy();

            // Call deploy() multiple times — phase must remain 'deployment'
            for (let i = 0; i < numCalls; i++) {
              manager.deploy();
            }
            expect(manager.getCurrentPhase()).toBe('deployment');
          }
        ),
        { numRuns: 200 }
      );
    });

    it('no sequence of deploy() calls from deployment can return to learning', () => {
      fc.assert(
        fc.property(
          fc.array(fc.constant('deploy'), { minLength: 1, maxLength: 100 }),
          (actions) => {
            // Start fresh, transition to deployment
            setupDOM();
            const sim = createMockSimulationEngine();
            const store = createMockStateStore();
            const manager = new UIManager(store, sim);
            manager.deploy();

            // Execute a sequence of deploy() calls
            for (const _action of actions) {
              manager.deploy();
              // After every call, phase must never be 'learning'
              expect(manager.getCurrentPhase()).not.toBe('learning');
            }
            // Final state must be deployment
            expect(manager.getCurrentPhase()).toBe('deployment');
          }
        ),
        { numRuns: 200 }
      );
    });

    it('the phase is always either learning or deployment (never anything else)', () => {
      fc.assert(
        fc.property(
          fc.boolean(),
          fc.integer({ min: 0, max: 20 }),
          (shouldDeploy, extraCalls) => {
            setupDOM();
            const sim = createMockSimulationEngine();
            const store = createMockStateStore();
            const manager = new UIManager(store, sim);

            // Phase must be valid after construction
            expect(['learning', 'deployment']).toContain(manager.getCurrentPhase());

            if (shouldDeploy) {
              manager.deploy();
            }

            // Phase must still be valid
            expect(['learning', 'deployment']).toContain(manager.getCurrentPhase());

            // After additional deploy() calls, phase remains valid
            for (let i = 0; i < extraCalls; i++) {
              manager.deploy();
              expect(['learning', 'deployment']).toContain(manager.getCurrentPhase());
            }
          }
        ),
        { numRuns: 200 }
      );
    });

    it('simulation engine start is called exactly once regardless of deploy attempts', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 30 }),
          (totalDeployCalls) => {
            setupDOM();
            const sim = createMockSimulationEngine();
            const store = createMockStateStore();
            const manager = new UIManager(store, sim);

            // Call deploy multiple times
            for (let i = 0; i < totalDeployCalls; i++) {
              manager.deploy();
            }

            // Simulation start should be called exactly once (first deploy)
            expect(sim.start).toHaveBeenCalledTimes(1);
            // Phase should be deployment
            expect(manager.getCurrentPhase()).toBe('deployment');
          }
        ),
        { numRuns: 200 }
      );
    });
  });
});

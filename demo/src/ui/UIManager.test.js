/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UIManager } from './UIManager.js';
import { eventBus, EVENTS } from '../utils/eventBus.js';

// Set up a minimal DOM for testing
function setupDOM() {
  document.body.innerHTML = `
    <div id="3d-container"></div>
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

describe('UIManager', () => {
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

  describe('constructor', () => {
    it('defaults phase to learning', () => {
      expect(uiManager.currentPhase).toBe('learning');
    });

    it('stores stateStore reference', () => {
      expect(uiManager.stateStore).toBe(mockStateStore);
    });

    it('stores simulationEngine reference', () => {
      expect(uiManager.simulationEngine).toBe(mockSimulation);
    });

    it('calls init() which shows learning phase', () => {
      const learningEl = document.getElementById('learning-phase');
      const deploymentEl = document.getElementById('deployment-phase');
      expect(learningEl.classList.contains('hidden')).toBe(false);
      expect(deploymentEl.classList.contains('hidden')).toBe(true);
    });
  });

  describe('init()', () => {
    it('shows learning-phase panel', () => {
      const el = document.getElementById('learning-phase');
      expect(el.classList.contains('hidden')).toBe(false);
    });

    it('hides deployment-phase panel', () => {
      const el = document.getElementById('deployment-phase');
      expect(el.classList.contains('hidden')).toBe(true);
    });

    it('binds deploy button click to deploy()', () => {
      const deploySpy = vi.spyOn(uiManager, 'deploy');
      const btn = document.getElementById('deploy-btn');
      btn.click();
      expect(deploySpy).toHaveBeenCalledTimes(1);
    });
  });

  describe('deploy()', () => {
    it('sets phase to deployment', () => {
      uiManager.deploy();
      expect(uiManager.currentPhase).toBe('deployment');
    });

    it('shows deployment phase panel', () => {
      uiManager.deploy();
      const el = document.getElementById('deployment-phase');
      expect(el.classList.contains('hidden')).toBe(false);
    });

    it('hides learning phase panel', () => {
      uiManager.deploy();
      const el = document.getElementById('learning-phase');
      expect(el.classList.contains('hidden')).toBe(true);
    });

    it('emits PHASE_CHANGE event via eventBus', () => {
      const handler = vi.fn();
      eventBus.on(EVENTS.PHASE_CHANGE, handler);
      uiManager.deploy();
      expect(handler).toHaveBeenCalledWith({ phase: 'deployment' });
      eventBus.off(EVENTS.PHASE_CHANGE, handler);
    });

    it('starts the simulation engine', () => {
      uiManager.deploy();
      expect(mockSimulation.start).toHaveBeenCalledTimes(1);
    });

    it('does nothing if already in deployment phase (no backward navigation)', () => {
      uiManager.deploy(); // first call
      mockSimulation.start.mockClear();

      uiManager.deploy(); // second call should do nothing
      expect(mockSimulation.start).not.toHaveBeenCalled();
    });
  });

  describe('showPhase()', () => {
    it('shows learning-phase and hides deployment-phase when phase is learning', () => {
      uiManager.showPhase('learning');
      const learningEl = document.getElementById('learning-phase');
      const deploymentEl = document.getElementById('deployment-phase');
      expect(learningEl.classList.contains('hidden')).toBe(false);
      expect(deploymentEl.classList.contains('hidden')).toBe(true);
    });

    it('shows deployment-phase and hides learning-phase when phase is deployment', () => {
      uiManager.showPhase('deployment');
      const learningEl = document.getElementById('learning-phase');
      const deploymentEl = document.getElementById('deployment-phase');
      expect(learningEl.classList.contains('hidden')).toBe(true);
      expect(deploymentEl.classList.contains('hidden')).toBe(false);
    });

    it('adds fullscreen class to 3d-container in deployment phase', () => {
      uiManager.showPhase('deployment');
      const container3d = document.getElementById('3d-container');
      expect(container3d.classList.contains('fullscreen')).toBe(true);
    });

    it('removes fullscreen class from 3d-container in learning phase', () => {
      uiManager.showPhase('deployment');
      uiManager.showPhase('learning');
      const container3d = document.getElementById('3d-container');
      expect(container3d.classList.contains('fullscreen')).toBe(false);
    });
  });

  describe('getCurrentPhase()', () => {
    it('returns learning initially', () => {
      expect(uiManager.getCurrentPhase()).toBe('learning');
    });

    it('returns deployment after deploy()', () => {
      uiManager.deploy();
      expect(uiManager.getCurrentPhase()).toBe('deployment');
    });
  });

  describe('reset()', () => {
    it('calls window.location.reload()', () => {
      // Mock window.location.reload
      const reloadMock = vi.fn();
      Object.defineProperty(window, 'location', {
        value: { reload: reloadMock },
        writable: true,
      });
      uiManager.reset();
      expect(reloadMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('Requirement 3.4: No backward navigation', () => {
    it('does not allow going back from deployment to learning via deploy()', () => {
      uiManager.deploy();
      expect(uiManager.currentPhase).toBe('deployment');

      // Attempt to call deploy again - should not re-trigger
      const handler = vi.fn();
      eventBus.on(EVENTS.PHASE_CHANGE, handler);
      uiManager.deploy();
      expect(handler).not.toHaveBeenCalled();
      eventBus.off(EVENTS.PHASE_CHANGE, handler);
    });

    it('currentPhase cannot be set back to learning through deploy', () => {
      uiManager.deploy();
      uiManager.deploy();
      uiManager.deploy();
      expect(uiManager.currentPhase).toBe('deployment');
    });
  });
});

import { eventBus, EVENTS } from '../utils/eventBus.js';

/**
 * UIManager handles phase transitions between Learning and Deployment phases.
 * 
 * Requirements:
 * - 3.1: Learning phase as initial view
 * - 3.2: Deploy button transitions to Deployment phase
 * - 3.3: Deploy transitions and starts simulation
 * - 3.4: No backward navigation from Deployment to Learning
 */
export class UIManager {
  /**
   * @param {import('../simulation/StateStore.js').StateStore} stateStore
   * @param {import('../simulation/SimulationEngine.js').SimulationEngine} simulationEngine
   */
  constructor(stateStore, simulationEngine) {
    /** @type {'learning' | 'deployment'} */
    this.currentPhase = 'learning';
    this.stateStore = stateStore;
    this.simulationEngine = simulationEngine;
    this.init();
  }

  /**
   * Initialize UI state: show learning phase, hide deployment phase,
   * and bind the Deploy button click handler.
   */
  init() {
    this.showPhase('learning');
    this._bindDeployButton();
  }

  /**
   * Bind the Deploy button click to trigger the deploy() method.
   * @private
   */
  _bindDeployButton() {
    const deployBtn = document.getElementById('deploy-btn');
    if (deployBtn) {
      deployBtn.addEventListener('click', () => this.deploy());
    }
  }

  /**
   * Transition from Learning to Deployment phase.
   * Sets phase to 'deployment', updates UI visibility,
   * emits PHASE_CHANGE event, and starts the simulation engine.
   * 
   * No backward navigation is allowed (Requirement 3.4).
   */
  deploy() {
    // Only allow forward transition from learning to deployment
    if (this.currentPhase !== 'learning') return;

    this.currentPhase = 'deployment';
    this.showPhase('deployment');
    eventBus.emit(EVENTS.PHASE_CHANGE, { phase: 'deployment' });
    this.simulationEngine.start();
  }

  /**
   * Toggle visibility of phase panels using the 'hidden' CSS class.
   * - learning-phase: visible when phase === 'learning', hidden otherwise
   * - deployment-phase: visible when phase === 'deployment', hidden otherwise
   * - 3d-container: expands to fullscreen in deployment phase
   * 
   * @param {'learning' | 'deployment'} phase - The phase to display
   */
  showPhase(phase) {
    const learningEl = document.getElementById('learning-phase');
    const deploymentEl = document.getElementById('deployment-phase');
    const container3d = document.getElementById('3d-container');

    if (learningEl) {
      learningEl.classList.toggle('hidden', phase !== 'learning');
    }
    if (deploymentEl) {
      deploymentEl.classList.toggle('hidden', phase !== 'deployment');
    }
    if (container3d) {
      container3d.classList.toggle('fullscreen', phase === 'deployment');
    }
  }

  /**
   * Returns the current phase string.
   * @returns {'learning' | 'deployment'}
   */
  getCurrentPhase() {
    return this.currentPhase;
  }

  /**
   * Reset the application by reloading the page.
   * This is the only way to go back to learning phase (Requirement 3.4).
   */
  reset() {
    window.location.reload();
  }
}

export default UIManager;

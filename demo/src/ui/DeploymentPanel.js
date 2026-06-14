import { formatTime } from '../utils/helpers.js';

/**
 * DeploymentPanel — renders and controls the deployment phase UI:
 * timeline scrubber, time display, play/pause toggle, and speed controls.
 *
 * Requirements: 7.2, 7.4, 7.5, 7.6, 14.5
 */
export class DeploymentPanel {
  /**
   * @param {import('./UIManager.js').UIManager} uiManager
   * @param {import('../simulation/SimulationEngine.js').SimulationEngine} simulation
   */
  constructor(uiManager, simulation) {
    // Support both (uiManager, simulation) and (simulation) signatures
    if (simulation === undefined) {
      this.simulation = uiManager;
      this.uiManager = null;
    } else {
      this.uiManager = uiManager;
      this.simulation = simulation;
    }

    /** @type {boolean} Whether the simulation is currently playing */
    this.isPlaying = true;

    this.render();
    this.bindPlayPause();
    this.bindSpeedControls();
    this.bindTimeline();
    this._bindTickUpdates();
  }

  /**
   * Render the deployment panel HTML into #timeline-panel.
   * Includes play/pause button, time display, speed buttons,
   * a range scrubber, scrubber markers, and event markers container.
   */
  render() {
    const container = document.getElementById('timeline-panel');
    if (!container) return;

    container.innerHTML = `
      <div class="timeline-controls">
        <button id="play-pause-btn" class="btn-accent" aria-label="Pause simulation">⏸</button>
        <span id="time-display">00:00</span>
        <div class="speed-controls-group">
          <button class="speed-btn" data-speed="1">1x</button>
          <button class="speed-btn" data-speed="10">10x</button>
          <button class="speed-btn active" data-speed="60">60x</button>
          <button class="speed-btn" data-speed="120">120x</button>
        </div>
      </div>
      <div class="timeline-scrubber-wrapper">
        <input type="range" id="timeline-scrubber" min="0" max="1439" step="1" value="0" class="timeline-scrubber" aria-label="Timeline scrubber" />
        <div class="scrubber-markers">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>23:59</span>
        </div>
      </div>
      <div id="event-markers"></div>
    `;
  }

  /**
   * Bind the timeline scrubber input event to simulation.seekTo().
   * When the user drags the scrubber, the simulation jumps to that minute.
   */
  bindTimeline() {
    const scrubber = document.getElementById('timeline-scrubber');
    if (!scrubber) return;

    scrubber.addEventListener('input', (e) => {
      const value = parseInt(e.target.value, 10);
      this.simulation.seekTo(value);
    });
  }

  /**
   * Bind speed control buttons to simulation.setSpeed().
   * Toggles the 'active' class to highlight the currently selected speed.
   */
  bindSpeedControls() {
    const buttons = document.querySelectorAll('.speed-btn');
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const speed = parseInt(btn.getAttribute('data-speed'), 10);
        this.simulation.setSpeed(speed);

        // Toggle active class
        buttons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  }

  /**
   * Bind the play/pause button to toggle simulation state.
   * Updates the button icon between ▶ (play) and ⏸ (pause).
   */
  bindPlayPause() {
    const btn = document.getElementById('play-pause-btn');
    if (!btn) return;

    btn.addEventListener('click', () => {
      if (this.isPlaying) {
        this.simulation.pause();
        this.isPlaying = false;
        btn.textContent = '▶';
        btn.setAttribute('aria-label', 'Play simulation');
      } else {
        this.simulation.resume();
        this.isPlaying = true;
        btn.textContent = '⏸';
        btn.setAttribute('aria-label', 'Pause simulation');
      }
    });
  }

  /**
   * Register a tick listener on the simulation to update the scrubber
   * position and time display on each simulation tick.
   * @private
   */
  _bindTickUpdates() {
    this.simulation.onTick((currentTimeMinutes) => {
      const scrubber = document.getElementById('timeline-scrubber');
      const timeDisplay = document.getElementById('time-display');
      const roundedMinutes = Math.floor(currentTimeMinutes);

      if (scrubber) {
        scrubber.value = roundedMinutes;
      }
      if (timeDisplay) {
        timeDisplay.textContent = formatTime(roundedMinutes);
      }
    });
  }
}

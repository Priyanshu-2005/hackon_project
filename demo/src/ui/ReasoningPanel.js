/**
 * ReasoningPanel — Glassmorphism overlay that displays Alexa's reasoning process
 * during the THINK stage of the SENSE-THINK-ACT-EXPLAIN pipeline.
 *
 * Shows contextual information about what Alexa is considering:
 * - Title (scenario name)
 * - Context info (who's home, what's happening)
 * - Prioritization decisions (devices kept on vs shed)
 * - Estimated duration
 *
 * Requirements: 12.4
 */
export class ReasoningPanel {
  constructor() {
    this.panel = document.getElementById('reasoning-panel');
    if (!this.panel) {
      this.panel = document.createElement('div');
      this.panel.id = 'reasoning-panel';
      this.panel.className = 'reasoning-panel hidden';
      document.body.appendChild(this.panel);
    }
    /** @type {number|null} Auto-hide timer ID */
    this._autoHideTimer = null;
  }

  /**
   * Show the reasoning panel with arbitrary HTML content.
   * Removes the 'hidden' class and sets innerHTML with glassmorphism content.
   * @param {string} content - HTML string to display inside the panel
   */
  show(content) {
    this._clearAutoHideTimer();
    this.panel.innerHTML = `<div class="reasoning-content glass-panel">${content}</div>`;
    this.panel.classList.remove('hidden');
  }

  /**
   * Hide the reasoning panel by adding the 'hidden' class.
   */
  hide() {
    this._clearAutoHideTimer();
    this.panel.classList.add('hidden');
  }

  /**
   * Show a formatted reasoning panel specific to the Power Cut scenario,
   * displaying the full SENSE-THINK-ACT-EXPLAIN reasoning chain.
   *
   * Auto-hides after 15 seconds.
   *
   * @param {string[]} prioritizedRooms - Array of room names that are prioritized
   */
  showPowerCutReasoning(prioritizedRooms) {
    const content = `
      <h3>⚡ Power Cut — Alexa's Reasoning</h3>
      <div class="reasoning-steps">
        <p>🧠 <strong>SENSE:</strong> Power grid failure detected. Arjun in online class. Battery 80%.</p>
        <p>🧠 <strong>THINK:</strong> Priority = Wi-Fi + Study Room. Shed AC + Geyser.</p>
        <p>⚡ <strong>ACT:</strong> AC OFF, Geyser OFF, Study lights → battery mode</p>
        <p>💬 <strong>EXPLAIN:</strong> Announcing to family...</p>
        <p><strong>Prioritized Rooms:</strong> ${prioritizedRooms.join(', ')}</p>
        <p><strong>Estimated backup:</strong> 2.5 hours at current load</p>
      </div>
    `;

    this.show(content);

    // Auto-hide after 15 seconds
    this._autoHideTimer = setTimeout(() => {
      this.hide();
    }, 15000);
  }

  /**
   * Clear the auto-hide timer if active.
   * @private
   */
  _clearAutoHideTimer() {
    if (this._autoHideTimer !== null) {
      clearTimeout(this._autoHideTimer);
      this._autoHideTimer = null;
    }
  }
}

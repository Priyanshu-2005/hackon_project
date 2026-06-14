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
  }

  /**
   * Show the reasoning overlay with structured data.
   * @param {object} reasoningData
   * @param {string} reasoningData.title - Scenario title (e.g. "Power Cut Detected")
   * @param {string[]} reasoningData.context - Context observations (who's home, activities)
   * @param {object} reasoningData.prioritization - Devices kept on vs shed
   * @param {string[]} reasoningData.prioritization.keepOn - Devices/rooms to keep powered
   * @param {string[]} reasoningData.prioritization.shed - Devices/rooms to power down
   * @param {string} reasoningData.estimatedDuration - Human-readable duration estimate
   */
  show(reasoningData) {
    const { title, context, prioritization, estimatedDuration } = reasoningData;

    const contextItems = (context || [])
      .map((item) => `<li>${item}</li>`)
      .join('');

    const keepOnItems = (prioritization?.keepOn || [])
      .map((item) => `<li class="reasoning-keep">✅ ${item}</li>`)
      .join('');

    const shedItems = (prioritization?.shed || [])
      .map((item) => `<li class="reasoning-shed">❌ ${item}</li>`)
      .join('');

    this.panel.innerHTML = `
      <div class="reasoning-content glass-panel">
        <div class="reasoning-header">
          <span class="reasoning-icon">🧠</span>
          <h3 class="reasoning-title">${title || 'Alexa is Thinking...'}</h3>
        </div>
        <div class="reasoning-stage-label">THINK</div>
        <div class="reasoning-section">
          <h4>Context Awareness</h4>
          <ul class="reasoning-context-list">${contextItems}</ul>
        </div>
        <div class="reasoning-section">
          <h4>Prioritization</h4>
          <div class="reasoning-priority-grid">
            <div class="reasoning-priority-col">
              <span class="reasoning-col-label">Keep On (Inverter)</span>
              <ul>${keepOnItems}</ul>
            </div>
            <div class="reasoning-priority-col">
              <span class="reasoning-col-label">Shed (Save Power)</span>
              <ul>${shedItems}</ul>
            </div>
          </div>
        </div>
        ${estimatedDuration ? `
        <div class="reasoning-section reasoning-duration">
          <span>⏱️ Estimated backup duration: <strong>${estimatedDuration}</strong></span>
        </div>
        ` : ''}
      </div>
    `;

    this.panel.classList.remove('hidden');
    this.panel.classList.add('visible');
  }

  /**
   * Hide the reasoning panel.
   */
  hide() {
    this.panel.classList.remove('visible');
    this.panel.classList.add('hidden');
  }
}

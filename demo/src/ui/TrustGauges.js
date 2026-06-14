/**
 * TrustGauges — Displays circular SVG gauge rings for each device category's
 * trust score and autonomy tier.
 *
 * Each gauge shows:
 * - Category name
 * - Circular progress ring (SVG circle)
 * - Score value (0-100) in center
 * - Tier number (1-5)
 *
 * Subscribes to StateStore trust updates and animates gauge changes
 * via stroke-dashoffset transitions.
 *
 * Requirements: 9.1, 9.2, 9.3
 */

/** Device categories to display gauges for */
const CATEGORIES = [
  'climate',
  'lighting',
  'security',
  'kitchen',
  'utility',
  'power',
  'entertainment',
  'assistant',
];

/** SVG ring geometry */
const RING_RADIUS = 28;
const RING_STROKE = 4;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;
const SVG_SIZE = 70;

export class TrustGauges {
  /**
   * @param {import('../simulation/StateStore.js').StateStore} stateStore
   */
  constructor(stateStore) {
    this.stateStore = stateStore;
    this.gaugeElements = new Map(); // category → { circle, scoreText, tierText }
    this.render();
    this.subscribeToUpdates();
  }

  /**
   * Create the gauge HTML within #trust-gauges container.
   * Each gauge has a title, SVG circle ring, score value, and tier number.
   */
  render() {
    const container = document.getElementById('trust-gauges');
    if (!container) return;

    // Build DOM programmatically for better compatibility with test environments
    container.innerHTML = '';

    // Title
    const title = document.createElement('h3');
    title.className = 'trust-gauges-title';
    title.textContent = 'Trust Scores';
    container.appendChild(title);

    // Grid container
    const grid = document.createElement('div');
    grid.className = 'trust-gauges-grid';
    container.appendChild(grid);

    // Create each gauge
    for (const category of CATEGORIES) {
      const gaugeEl = this._createGaugeElement(category);
      grid.appendChild(gaugeEl);

      // Cache references
      const circle = gaugeEl.querySelector('.gauge-progress');
      const scoreText = gaugeEl.querySelector('.gauge-score');
      const tierText = gaugeEl.querySelector('.gauge-tier');
      this.gaugeElements.set(category, { circle, scoreText, tierText });
    }
  }

  /**
   * Create a single gauge DOM element with SVG ring.
   * @param {string} category
   * @returns {HTMLElement}
   */
  _createGaugeElement(category) {
    const displayName = category.charAt(0).toUpperCase() + category.slice(1);
    const center = SVG_SIZE / 2;

    const wrapper = document.createElement('div');
    wrapper.className = 'trust-gauge';
    wrapper.setAttribute('data-gauge', category);

    // SVG element
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', String(SVG_SIZE));
    svg.setAttribute('height', String(SVG_SIZE));
    svg.setAttribute('viewBox', `0 0 ${SVG_SIZE} ${SVG_SIZE}`);

    // Background circle
    const bgCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    bgCircle.setAttribute('cx', String(center));
    bgCircle.setAttribute('cy', String(center));
    bgCircle.setAttribute('r', String(RING_RADIUS));
    bgCircle.setAttribute('fill', 'none');
    bgCircle.setAttribute('stroke', 'rgba(0,202,255,0.1)');
    bgCircle.setAttribute('stroke-width', String(RING_STROKE));
    svg.appendChild(bgCircle);

    // Progress circle
    const progressCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    progressCircle.classList.add('gauge-progress');
    progressCircle.setAttribute('cx', String(center));
    progressCircle.setAttribute('cy', String(center));
    progressCircle.setAttribute('r', String(RING_RADIUS));
    progressCircle.setAttribute('fill', 'none');
    progressCircle.setAttribute('stroke', '#00CAFF');
    progressCircle.setAttribute('stroke-width', String(RING_STROKE));
    progressCircle.setAttribute('stroke-dasharray', String(RING_CIRCUMFERENCE));
    progressCircle.setAttribute('stroke-dashoffset', String(RING_CIRCUMFERENCE));
    progressCircle.setAttribute('stroke-linecap', 'round');
    progressCircle.setAttribute('transform', `rotate(-90 ${center} ${center})`);
    svg.appendChild(progressCircle);

    // Score text in center
    const scoreText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    scoreText.classList.add('gauge-score');
    scoreText.setAttribute('x', String(center));
    scoreText.setAttribute('y', String(center));
    scoreText.setAttribute('text-anchor', 'middle');
    scoreText.setAttribute('dominant-baseline', 'central');
    scoreText.setAttribute('fill', '#e6edf3');
    scoreText.setAttribute('font-size', '12');
    scoreText.setAttribute('font-weight', '600');
    scoreText.setAttribute('font-family', 'Inter, sans-serif');
    scoreText.textContent = '0';
    svg.appendChild(scoreText);

    wrapper.appendChild(svg);

    // Category name
    const nameSpan = document.createElement('span');
    nameSpan.className = 'gauge-category-name';
    nameSpan.textContent = displayName;
    wrapper.appendChild(nameSpan);

    // Tier badge
    const tierSpan = document.createElement('span');
    tierSpan.className = 'gauge-tier';
    tierSpan.textContent = 'Tier 1';
    wrapper.appendChild(tierSpan);

    return wrapper;
  }

  /**
   * Subscribe to StateStore trust updates for each category.
   * When trust:{category} fires, animate the corresponding gauge.
   */
  subscribeToUpdates() {
    for (const category of CATEGORIES) {
      this.stateStore.on(`trust:${category}`, (data) => {
        this.updateGauge(category, data);
      });
    }
  }

  /**
   * Update a single gauge's SVG ring and text to reflect a new score/tier.
   * Animates the stroke-dashoffset for a smooth fill transition.
   *
   * @param {string} category
   * @param {{ score: number, tier: number }} data
   */
  updateGauge(category, { score, tier }) {
    const elements = this.gaugeElements.get(category);
    if (!elements) return;

    const { circle, scoreText, tierText } = elements;

    // Calculate the new offset based on score (0-100), clamped
    const percentage = Math.max(0, Math.min(100, score)) / 100;
    const newOffset = RING_CIRCUMFERENCE * (1 - percentage);

    // Animate the circle stroke-dashoffset via CSS transition
    if (circle) {
      circle.style.transition = 'stroke-dashoffset 0.6s ease-out';
      circle.setAttribute('stroke-dashoffset', String(newOffset));
    }

    // Update score text
    if (scoreText) {
      scoreText.textContent = String(Math.round(score));
    }

    // Update tier display
    if (tierText) {
      tierText.textContent = `Tier ${tier}`;
    }
  }

  /**
   * Accept initial tier data (from DataLayer.getAutonomyTiers()) to set starting gauge values.
   * @param {{ tiers: Array<{ category: string, currentTier: number, trustScore: number }> }} tiersData
   */
  initializeFromData(tiersData) {
    if (!tiersData || !tiersData.tiers) return;

    for (const tierEntry of tiersData.tiers) {
      const { category, currentTier, trustScore } = tierEntry;
      if (CATEGORIES.includes(category)) {
        // Set the state store so it's in sync
        this.stateStore.trustScores.set(category, { score: trustScore, tier: currentTier });
        // Update the gauge visually
        this.updateGauge(category, { score: trustScore, tier: currentTier });
      }
    }
  }
}

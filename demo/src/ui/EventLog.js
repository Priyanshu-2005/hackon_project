/**
 * EventLog — Right sidebar panel displaying chronological proactive action entries.
 *
 * Subscribes to StateStore 'eventlog' events and renders each entry with:
 * - Timestamp [HH:MM]
 * - Action name with emoji based on type
 * - Target device line: "→ {device}"
 * - Reasoning line: "→ Reason: {reasoning}"
 * - Type/tier badge (styled with Alexa blue background)
 * - Optional "Override" button that:
 *   a. Removes the entry visually (strikethrough)
 *   b. Calls stateStore.updateTrustScore(category, -15) to reduce trust
 *
 * Auto-scrolls to the bottom when new entries arrive.
 * Entries have visual variety based on actionType (emoji icons).
 *
 * Styled with glassmorphism sub-cards and border-left accent color per action type.
 *
 * Requirements: 7.3, 8.1
 */
import { formatTime } from '../utils/helpers.js';

export class EventLog {
  /**
   * @param {import('../simulation/StateStore.js').StateStore} stateStore
   */
  constructor(stateStore) {
    this.stateStore = stateStore;
    this.container = document.getElementById('event-log-panel');
    this.entriesContainer = null;

    this.render();
    this.stateStore.on('eventlog', (entry) => this.addEntry(entry));
  }

  /**
   * Creates the HTML structure inside #event-log-panel:
   * - Title header: "📋 Event Log"
   * - Scrollable entries container (#event-log-entries)
   */
  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="event-log-header">
        <h3 class="event-log-title">📋 Event Log</h3>
        <button class="event-log-close" aria-label="Close event log" title="Hide event log">✕</button>
      </div>
      <div id="event-log-entries" class="event-log-entries"></div>
    `;

    this.entriesContainer = this.container.querySelector('#event-log-entries');

    // Wire the close button to hide the panel
    const closeBtn = this.container.querySelector('.event-log-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.hide());
    }
  }

  /**
   * Hide the event log panel.
   */
  hide() {
    if (this.container) {
      this.container.classList.add('hidden');
    }
  }

  /**
   * Show the event log panel.
   */
  show() {
    if (this.container) {
      this.container.classList.remove('hidden');
    }
  }

  /**
   * Creates a DOM element for a log entry and appends it to the entries container.
   *
   * Each entry card contains:
   * - [HH:MM] timestamp
   * - Action name in bold with emoji
   * - Device target line: "→ {device}"
   * - Reason line: "→ Reason: {reasoning}"
   * - Type/tier badge with Alexa blue background
   * - Override button for trust score reduction
   *
   * @param {object} entry — { time, action, device, reasoning, type, tier?, confidence?, stage?, category? }
   */
  addEntry(entry) {
    if (!this.entriesContainer) return;

    const el = document.createElement('div');
    el.className = 'event-log-entry';

    const accentColor = this.getAccentColor(entry.type);
    el.style.borderLeftColor = accentColor;

    const emoji = this.getEmoji(entry.type);
    const timestamp = this.formatTime(entry.time);

    // Header row
    const header = document.createElement('div');
    header.className = 'event-log-entry-header';

    const timeSpan = document.createElement('span');
    timeSpan.className = 'event-log-time';
    timeSpan.textContent = timestamp;
    header.appendChild(timeSpan);

    // Meta info (stage, tier, confidence)
    if (entry.stage || entry.tier !== undefined || entry.confidence !== undefined) {
      const meta = document.createElement('div');
      meta.className = 'event-log-meta';

      if (entry.stage) {
        const stageSpan = document.createElement('span');
        stageSpan.className = 'event-log-stage';
        stageSpan.textContent = `[${entry.stage}]`;
        meta.appendChild(stageSpan);
      }
      if (entry.tier !== undefined) {
        const tierSpan = document.createElement('span');
        tierSpan.className = 'event-log-tier';
        tierSpan.textContent = `Tier ${entry.tier}`;
        meta.appendChild(tierSpan);
      }
      if (entry.confidence !== undefined) {
        const confSpan = document.createElement('span');
        confSpan.className = 'event-log-confidence';
        confSpan.textContent = `${Math.round(entry.confidence * 100)}%`;
        meta.appendChild(confSpan);
      }

      header.appendChild(meta);
    }

    el.appendChild(header);

    // Action row (emoji + name)
    const actionRow = document.createElement('div');
    actionRow.className = 'event-log-entry-action';

    const emojiSpan = document.createElement('span');
    emojiSpan.className = 'event-log-emoji';
    emojiSpan.textContent = emoji;
    actionRow.appendChild(emojiSpan);

    const actionName = document.createElement('span');
    actionName.className = 'event-log-action-name';
    actionName.textContent = entry.action || 'Unknown Action';
    actionRow.appendChild(actionName);

    el.appendChild(actionRow);

    // Device target line
    const deviceDiv = document.createElement('div');
    deviceDiv.className = 'event-log-device';
    deviceDiv.textContent = `→ ${entry.device || ''}`;
    el.appendChild(deviceDiv);

    // Reasoning line
    const reasoningDiv = document.createElement('div');
    reasoningDiv.className = 'event-log-reasoning';
    reasoningDiv.textContent = `→ Reason: ${entry.reasoning || ''}`;
    el.appendChild(reasoningDiv);

    // Badge row (type/tier badge + Override button)
    const badgeRow = document.createElement('div');
    badgeRow.className = 'event-log-badge-row';

    const badge = document.createElement('span');
    badge.className = 'event-log-type-badge';
    badge.textContent = this._getBadgeText(entry);
    badgeRow.appendChild(badge);

    const overrideBtn = document.createElement('button');
    overrideBtn.className = 'event-log-override-btn';
    overrideBtn.textContent = 'Override';
    overrideBtn.addEventListener('click', () => {
      this._handleOverride(el, entry);
    });
    badgeRow.appendChild(overrideBtn);

    el.appendChild(badgeRow);

    this.entriesContainer.appendChild(el);
    this.autoScroll();
  }

  /**
   * Handle override action: apply strikethrough and reduce trust score.
   * @param {HTMLElement} entryEl - The entry DOM element
   * @param {object} entry - The event entry data
   */
  _handleOverride(entryEl, entry) {
    // Apply strikethrough visual
    entryEl.classList.add('event-log-entry--overridden');

    // Determine category from entry (use entry.category or derive from type)
    const category = entry.category || this._categoryFromType(entry.type);

    // Reduce trust score by -15
    if (this.stateStore.updateTrustScore) {
      this.stateStore.updateTrustScore(category, -15);
    }

    // Disable the override button after use
    const btn = entryEl.querySelector('.event-log-override-btn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Overridden';
    }
  }

  /**
   * Map action type to device category for trust score updates.
   * @param {string} type
   * @returns {string}
   */
  _categoryFromType(type) {
    const typeToCategory = {
      ac_precool: 'climate',
      geyser_preheat: 'utility',
      security_arm: 'security',
      energy_optimization: 'power',
      comfort_lighting: 'lighting',
      power_cut: 'power',
    };
    return typeToCategory[type] || 'assistant';
  }

  /**
   * Build badge text showing type and tier info.
   * @param {object} entry
   * @returns {string}
   */
  _getBadgeText(entry) {
    const typeLabel = this._formatTypeName(entry.type);
    if (entry.tier !== undefined) {
      return `${typeLabel} • Tier ${entry.tier}`;
    }
    return typeLabel;
  }

  /**
   * Format a type string into a human-readable label.
   * @param {string} type
   * @returns {string}
   */
  _formatTypeName(type) {
    if (!type) return 'Action';
    return type
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  /**
   * Scrolls the entries container to the bottom to show the latest entry.
   */
  autoScroll() {
    if (this.entriesContainer) {
      this.entriesContainer.scrollTop = this.entriesContainer.scrollHeight;
    }
  }

  /**
   * Removes all entries from the event log.
   */
  clear() {
    if (this.entriesContainer) {
      this.entriesContainer.innerHTML = '';
    }
  }

  /**
   * Returns an emoji for the given action type.
   * @param {string} type
   * @returns {string}
   */
  getEmoji(type) {
    const emojiMap = {
      ac_precool: '❄️',
      geyser_preheat: '🔥',
      security_arm: '🔒',
      energy_optimization: '⚡',
      comfort_lighting: '💡',
      power_cut: '⚠️',
    };
    return emojiMap[type] || '🔔';
  }

  /**
   * Returns a CSS color string for the border-left accent per action type.
   * @param {string} type
   * @returns {string}
   */
  getAccentColor(type) {
    const colorMap = {
      ac_precool: '#00CAFF',
      geyser_preheat: '#FF6B35',
      security_arm: '#FFD700',
      energy_optimization: '#00FF88',
      comfort_lighting: '#FFB347',
      power_cut: '#FF4757',
    };
    return colorMap[type] || '#00CAFF';
  }

  /**
   * Format minutes (0–1439) as [HH:MM].
   * Uses formatTime from helpers.js.
   * @param {number} minutes
   * @returns {string}
   */
  formatTime(minutes) {
    if (typeof minutes !== 'number' || isNaN(minutes)) return '[--:--]';
    return `[${formatTime(minutes)}]`;
  }
}

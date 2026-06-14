/**
 * EventLog — Right sidebar panel displaying chronological proactive action entries.
 *
 * Subscribes to StateStore 'eventlog' events and renders each entry with:
 * - Timestamp [HH:MM]
 * - Action name with emoji based on type
 * - Target device name
 * - Reasoning text (muted)
 * - Confidence/tier info if available
 *
 * Styled with glassmorphism sub-cards and border-left accent color per action type.
 *
 * Requirements: 7.3, 8.1
 */
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
   * - Title header: "Event Log"
   * - Scrollable entries container (#event-log-entries)
   */
  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="event-log-header">
        <h3 class="event-log-title">📋 Event Log</h3>
      </div>
      <div id="event-log-entries" class="event-log-entries"></div>
    `;

    this.entriesContainer = this.container.querySelector('#event-log-entries');
  }

  /**
   * Creates a DOM element for a log entry and appends it to the entries container.
   *
   * @param {object} entry — { time, action, device, reasoning, type, stage? }
   */
  addEntry(entry) {
    if (!this.entriesContainer) return;

    const el = document.createElement('div');
    el.className = 'event-log-entry';

    const accentColor = this.getAccentColor(entry.type);
    el.style.borderLeftColor = accentColor;

    const emoji = this.getEmoji(entry.type);
    const timestamp = this.formatTime(entry.time);

    // Build confidence/tier info line
    let metaLine = '';
    if (entry.stage) {
      metaLine += `<span class="event-log-stage">[${entry.stage}]</span>`;
    }
    if (entry.tier !== undefined) {
      metaLine += `<span class="event-log-tier">Tier ${entry.tier}</span>`;
    }
    if (entry.confidence !== undefined) {
      metaLine += `<span class="event-log-confidence">${Math.round(entry.confidence * 100)}%</span>`;
    }

    el.innerHTML = `
      <div class="event-log-entry-header">
        <span class="event-log-time">${timestamp}</span>
        ${metaLine ? `<div class="event-log-meta">${metaLine}</div>` : ''}
      </div>
      <div class="event-log-entry-action">
        <span class="event-log-emoji">${emoji}</span>
        <span class="event-log-action-name">${entry.action || 'Unknown Action'}</span>
      </div>
      <div class="event-log-device">${entry.device || ''}</div>
      <div class="event-log-reasoning">${entry.reasoning || ''}</div>
    `;

    this.entriesContainer.appendChild(el);
    this.autoScroll();
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
      power_cut: '🧠',
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
   * @param {number} minutes
   * @returns {string}
   */
  formatTime(minutes) {
    if (typeof minutes !== 'number' || isNaN(minutes)) return '[--:--]';
    const h = Math.floor(minutes / 60).toString().padStart(2, '0');
    const m = Math.floor(minutes % 60).toString().padStart(2, '0');
    return `[${h}:${m}]`;
  }
}

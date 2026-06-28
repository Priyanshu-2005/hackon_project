import { eventBus as defaultEventBus, EVENTS } from '../utils/eventBus.js';
import { predictFromCsv } from '../data/csvPredict.js';
import { SAMPLE_CSV, SAMPLE_CSV_FILENAME } from '../data/sampleCsv.js';

/**
 * Family members shown first (in this order) in the learned-routines list.
 * Any other member found in an uploaded CSV is appended after these.
 */
const FAMILY_MEMBERS = ['Rajesh', 'Priya', 'Arjun', 'Ananya', 'Dadaji', 'Dadiji'];

/**
 * Default learned routines representing the Sharma family's typical week.
 * These are the "mock" routines Alexa shows before any CSV is uploaded — they
 * are fully visible in the Learning Phase and get replaced by the predictions
 * derived from an uploaded activity log.
 */
const DEFAULT_EVENTS = [
  // Rajesh
  { id: 'default-1', member: 'Rajesh', type: 'Wake up', time: '06:30', room: 'Master Bedroom', devices: ['Lights', 'Geyser'] },
  { id: 'default-2', member: 'Rajesh', type: 'Leave home', time: '08:00', room: 'Balcony', devices: ['Lock', 'Camera'] },
  { id: 'default-3', member: 'Rajesh', type: 'Arrive home', time: '18:30', room: 'Balcony', devices: ['Lock', 'AC', 'Lights'] },
  { id: 'default-4', member: 'Rajesh', type: 'Bedtime', time: '23:00', room: 'Master Bedroom', devices: ['AC', 'Lights'] },

  // Priya
  { id: 'default-5', member: 'Priya', type: 'Wake up', time: '06:00', room: 'Master Bedroom', devices: ['Lights', 'Geyser'] },
  { id: 'default-6', member: 'Priya', type: 'Start cooking', time: '07:00', room: 'Kitchen', devices: ['Kitchen Hub', 'Lights'] },
  { id: 'default-7', member: 'Priya', type: 'Start cooking', time: '12:00', room: 'Kitchen', devices: ['Kitchen Hub', 'Lights'] },
  { id: 'default-8', member: 'Priya', type: 'Bedtime', time: '22:30', room: 'Master Bedroom', devices: ['AC', 'Lights'] },

  // Arjun
  { id: 'default-9', member: 'Arjun', type: 'Wake up', time: '07:00', room: 'Kids Room', devices: ['Lights'] },
  { id: 'default-10', member: 'Arjun', type: 'Online class', time: '16:00', room: 'Study Room', devices: ['Lights', 'AC', 'Echo'] },
  { id: 'default-11', member: 'Arjun', type: 'Bedtime', time: '22:00', room: 'Kids Room', devices: ['Lights', 'AC'] },

  // Ananya
  { id: 'default-12', member: 'Ananya', type: 'Wake up', time: '07:30', room: 'Kids Room', devices: ['Lights'] },
  { id: 'default-13', member: 'Ananya', type: 'TV time', time: '15:00', room: 'Living Room', devices: ['TV', 'Lights'] },
  { id: 'default-14', member: 'Ananya', type: 'Bedtime', time: '21:00', room: 'Kids Room', devices: ['Lights', 'AC'] },

  // Dadaji
  { id: 'default-15', member: 'Dadaji', type: 'Wake up', time: '06:00', room: 'Master Bedroom', devices: ['Lights'] },
  { id: 'default-16', member: 'Dadaji', type: 'Afternoon rest', time: '13:00', room: 'Living Room', devices: ['AC', 'Lights'] },
  { id: 'default-17', member: 'Dadaji', type: 'Bedtime', time: '21:30', room: 'Master Bedroom', devices: ['AC', 'Lights'] },

  // Dadiji
  { id: 'default-18', member: 'Dadiji', type: 'Wake up', time: '05:30', room: 'Master Bedroom', devices: ['Lights'] },
  { id: 'default-19', member: 'Dadiji', type: 'Custom', time: '06:00', room: 'Balcony', devices: ['Lights'], customLabel: 'Prayer' },
  { id: 'default-20', member: 'Dadiji', type: 'Bedtime', time: '21:00', room: 'Master Bedroom', devices: ['Lights', 'AC'] },
];

/**
 * LearningPanel — Learning Phase UI.
 *
 * Instead of a manual event-entry form, Alexa shows the household routines it
 * has "learned" (the mock defaults) and lets the user upload last week's
 * activity log (CSV). The CSV is sent to Amazon Bedrock (real mode) — or
 * analyzed on-device as a fallback — to predict today's routines and derive
 * the proactive actions Alexa will take during the Deployment Phase.
 *
 * Requirements: 4.1, 4.4, 4.5, 4.6
 */
export class LearningPanel {
  /**
   * @param {import('./UIManager.js').UIManager} uiManager — used to call deploy()
   * @param {import('../utils/eventBus.js').EventBus} [eventBusInstance]
   * @param {import('../data/DataLayer.js').DataLayer} [dataLayer] — for real-mode
   *   CSV prediction via the backend; optional (falls back to on-device prediction).
   */
  constructor(uiManager, eventBusInstance, dataLayer) {
    this.uiManager = uiManager;
    this.eventBus = eventBusInstance || defaultEventBus;
    this.dataLayer = dataLayer || null;

    /** @type {Array<{id: string, member: string, type: string, time: string, room: string, devices: string[]}>} */
    this.events = [...DEFAULT_EVENTS];

    /** @type {Array<object>} Proactive actions derived from an uploaded CSV (empty until upload). */
    this.proactiveActions = [];

    this.render();
    this.bindEvents();
  }

  /**
   * Add a routine to the list (kept for programmatic use / tests).
   */
  addEvent(eventData) {
    const event = {
      id: 'evt-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8),
      ...eventData,
    };
    this.events.push(event);
    this.renderEventList();
    this.updateCounter();
    this.eventBus.emit(EVENTS.EVENT_ADDED, event);
  }

  /**
   * Remove a routine by id (kept for programmatic use / tests).
   */
  removeEvent(id) {
    const removed = this.events.find((e) => e.id === id);
    this.events = this.events.filter((e) => e.id !== id);
    this.renderEventList();
    this.updateCounter();
    if (removed) {
      this.eventBus.emit(EVENTS.EVENT_REMOVED, removed);
    }
  }

  /**
   * Render the panel header + CSV upload section into #event-form.
   */
  render() {
    const formEl = document.getElementById('event-form');
    if (!formEl) return;

    const uniqueMembers = new Set(this.events.map((e) => e.member)).size;

    formEl.innerHTML = `
      <div class="learning-panel-header">
        <h3>Alexa is learning your household</h3>
        <p id="routine-counter" class="routine-counter">Alexa has learned ${this.events.length} routines for ${uniqueMembers} family members</p>
      </div>

      <div class="csv-upload-section">
        <h4>📂 Upload last week's activity log</h4>
        <p class="csv-help">
          Alexa sends your household's previous-week routine to Amazon Bedrock to
          predict today's events and decide what to do <em>ahead of time</em>.
        </p>
        <details class="csv-format">
          <summary>CSV format</summary>
          <ul>
            <li>Columns: <code>date, time, member, event_type, room, devices</code></li>
            <li><code>date</code> = YYYY-MM-DD (last 7 days), <code>time</code> = HH:MM</li>
            <li><code>devices</code> is optional, pipe-separated e.g. <code>Lights|Geyser</code></li>
          </ul>
          <code class="csv-example">date,time,member,event_type,room,devices
2026-06-13,06:00,Priya,Wake up,Master Bedroom,Lights|Geyser
2026-06-13,08:00,Rajesh,Leave home,Balcony,Lock|Camera</code>
        </details>
        <div class="csv-controls">
          <input type="file" id="csv-file-input" accept=".csv,text/csv" aria-label="Activity log CSV file" />
          <button type="button" id="csv-analyze-btn" class="btn-ghost">Analyze with Bedrock</button>
        </div>
        <button type="button" id="csv-download-btn" class="csv-sample-link">⬇ Download sample CSV</button>
        <div id="csv-status" class="csv-status csv-status-info"></div>
      </div>

      <h4 class="routines-heading">Learned routines</h4>
    `;

    this.renderEventList();
  }

  /**
   * Render the learned routines into #event-list, grouped by family member
   * and sorted by time. Shows a confidence badge when available (from a CSV).
   */
  renderEventList() {
    const listEl = document.getElementById('event-list');
    if (!listEl) return;

    if (this.events.length === 0) {
      listEl.innerHTML = '<p class="event-list-empty">No routines learned yet.</p>';
      return;
    }

    // Group by member; keep FAMILY_MEMBERS order, then any extra members found.
    const grouped = {};
    for (const evt of this.events) {
      (grouped[evt.member] = grouped[evt.member] || []).push(evt);
    }
    const extras = Object.keys(grouped).filter((m) => !FAMILY_MEMBERS.includes(m)).sort();
    const memberOrder = [...FAMILY_MEMBERS, ...extras];

    let html = '';
    for (const member of memberOrder) {
      const items = grouped[member];
      if (!items || items.length === 0) continue;
      items.sort((a, b) => (a.time || '').localeCompare(b.time || ''));

      html += `<div class="event-group">
        <h4 class="event-group-title">${member}</h4>`;
      for (const evt of items) {
        const typeLabel = evt.type === 'Custom' && evt.customLabel ? `Custom/${evt.customLabel}` : evt.type;
        const conf = typeof evt.confidence === 'number'
          ? `<span class="event-confidence" title="Pattern confidence">${Math.round(evt.confidence * 100)}%</span>`
          : '';
        html += `<div class="event-item" data-id="${evt.id}">
          <div class="event-item-info">
            <span class="event-time">${evt.time}</span>
            <span class="event-type">${typeLabel}</span>
            <span class="event-room">${evt.room}</span>
            <span class="event-devices">${(evt.devices || []).join(', ')}</span>
          </div>
          ${conf}
        </div>`;
      }
      html += '</div>';
    }

    listEl.innerHTML = html;
  }

  /**
   * Update the "Alexa has learned X routines for Y family members" counter.
   */
  updateCounter() {
    const counterEl = document.getElementById('routine-counter');
    if (!counterEl) return;
    const uniqueMembers = new Set(this.events.map((e) => e.member)).size;
    counterEl.textContent = `Alexa has learned ${this.events.length} routines for ${uniqueMembers} family members`;
  }

  /**
   * Set the CSV status line text + style.
   * @param {string} html
   * @param {'info'|'success'|'error'} kind
   */
  _setStatus(html, kind = 'info') {
    const el = document.getElementById('csv-status');
    if (!el) return;
    el.className = `csv-status csv-status-${kind}`;
    el.innerHTML = html;
  }

  /**
   * Convert backend/local predictions into the routine shape this panel renders.
   * @param {Array} predictions
   */
  _predictionsToEvents(predictions) {
    return predictions.map((p, i) => ({
      id: 'pred-' + i,
      member: p.member,
      type: p.event_type,
      time: p.predicted_time || p.time || '--:--',
      room: p.room,
      devices: p.devices || [],
      confidence: typeof p.confidence === 'number' ? p.confidence : undefined,
    }));
  }

  /**
   * Trigger a download of the bundled sample activity-log CSV so users can see
   * the expected format (and try the upload flow immediately).
   */
  _downloadSample() {
    const blob = new Blob([SAMPLE_CSV], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = SAMPLE_CSV_FILENAME;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Read the selected CSV and predict today's routines + proactive actions.
   * Real mode → backend (Amazon Bedrock); otherwise (or on failure) → on-device.
   */
  async _analyzeCsv() {
    const input = document.getElementById('csv-file-input');
    const file = input && input.files && input.files[0];
    if (!file) {
      this._setStatus('Choose a CSV file first.', 'error');
      return;
    }

    this._setStatus('⏳ Analyzing your routines with Amazon Bedrock…', 'info');

    let text;
    try {
      text = await file.text();
    } catch (_) {
      this._setStatus('Could not read the selected file.', 'error');
      return;
    }

    let result = null;
    let usedBackend = false;
    const useReal = this.dataLayer && this.dataLayer.mode === 'real' && this.dataLayer.apiProvider;

    if (useReal) {
      try {
        result = await this.dataLayer.apiProvider.predictEventsFromCsv(text);
        usedBackend = true;
      } catch (err) {
        console.warn('Backend prediction failed, falling back to on-device prediction:', err);
      }
    }

    if (!result) {
      try {
        result = predictFromCsv(text);
      } catch (err) {
        this._setStatus(`Could not parse CSV: ${err.message}`, 'error');
        return;
      }
    }

    if (result.errors && result.errors.length) {
      const items = result.errors.slice(0, 6).map((e) => `<li>${e}</li>`).join('');
      this._setStatus(`CSV could not be used:<ul>${items}</ul>`, 'error');
      return;
    }

    const predictions = result.predictions || [];
    if (!predictions.length) {
      this._setStatus('No recurring routines found in this CSV.', 'error');
      return;
    }

    // Replace the visible learned routines + store proactive actions for deploy.
    this.events = this._predictionsToEvents(predictions);
    this.proactiveActions = result.proactive_actions || [];
    this.renderEventList();
    this.updateCounter();

    const engine = result.ai_enhanced
      ? 'Amazon Bedrock (Claude)'
      : (usedBackend ? 'the statistical model' : 'on-device analysis');
    this._setStatus(
      `✅ Learned <strong>${predictions.length}</strong> routines from ` +
      `<strong>${result.days_analyzed || '?'}</strong> days of history — powered by ${engine}. ` +
      `Press <strong>Deploy</strong> to watch Alexa think ahead.`,
      'success'
    );
  }

  /**
   * Wire the CSV analyze button and the Deploy button.
   */
  bindEvents() {
    const analyzeBtn = document.getElementById('csv-analyze-btn');
    if (analyzeBtn) {
      analyzeBtn.addEventListener('click', () => this._analyzeCsv());
    }

    const downloadBtn = document.getElementById('csv-download-btn');
    if (downloadBtn) {
      downloadBtn.addEventListener('click', () => this._downloadSample());
    }

    // Deploy → transition phase and hand the derived proactive actions to the
    // scheduler (main.js loads payload.proactiveActions when present).
    const deployBtn = document.getElementById('deploy-btn');
    if (deployBtn) {
      deployBtn.addEventListener('click', () => {
        if (this.uiManager) {
          this.uiManager.deploy();
        }
        this.eventBus.emit(EVENTS.PHASE_CHANGE, {
          phase: 'deployment',
          events: this.events,
          proactiveActions: this.proactiveActions,
        });
      });
    }
  }

  /**
   * Returns the current list of learned routines.
   * @returns {Array}
   */
  getEvents() {
    return [...this.events];
  }
}

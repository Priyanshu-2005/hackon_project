#!/usr/bin/env bash
#
# Apply the CSV-upload / Learning-Phase changes to the frontend on the AWS
# instance (no git required). Run from the frontend "demo/" root:
#     bash aws_apply_changes.sh
#
set -euo pipefail

if [ ! -f package.json ] || [ ! -d src ]; then
  echo "ERROR: run this from the demo/ project root (where package.json + src/ live)." >&2
  exit 1
fi

echo "==> Writing source files"
echo "  -> src/data/csvPredict.js"
cat > src/data/csvPredict.js <<'CSVPREDICT_EOF'
/**
 * csvPredict — client-side CSV → predictions → proactive actions.
 *
 * This is a faithful JavaScript port of the backend's
 * `src/intelligence/csv_predictor.py` (`predict` + `derive_proactive_actions`).
 *
 * It is used as a fallback so the CSV-upload demo keeps working in **mock mode**
 * (no backend) or whenever the real `/predict/events` call fails. In real mode
 * the backend (Amazon Bedrock Claude) is used instead — see ApiProvider.
 */

/** Split a "HH:MM" / "H:MM" string into minutes since midnight, or null. */
function parseTimeToMinutes(value) {
  const parts = String(value || '').trim().split(':');
  if (parts.length !== 2) return null;
  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return null;
  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return null;
  return hours * 60 + minutes;
}

/** Convert minutes since midnight to a zero-padded "HH:MM" string. */
function minutesToHHMM(minutes) {
  const m = Math.max(0, Math.min(1439, Math.round(minutes)));
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return `${String(h).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

/** Split a pipe/comma-separated devices cell into a clean list. */
function parseDevices(value) {
  if (!value) return [];
  return String(value)
    .replace(/,/g, '|')
    .split('|')
    .map((d) => d.trim())
    .filter(Boolean);
}

/**
 * Minimal CSV parser (handles quoted fields with commas).
 * @param {string} text
 * @returns {string[][]} rows of cells
 */
function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;
  const src = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (inQuotes) {
      if (ch === '"') {
        if (src[i + 1] === '"') { cell += '"'; i++; }
        else inQuotes = false;
      } else cell += ch;
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(cell); cell = '';
    } else if (ch === '\n') {
      row.push(cell); rows.push(row); row = []; cell = '';
    } else {
      cell += ch;
    }
  }
  if (cell.length > 0 || row.length > 0) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.some((c) => c.trim() !== ''));
}

const REQUIRED_COLUMNS = ['date', 'time', 'member', 'event_type', 'room'];

/**
 * Parse + lightly validate the CSV text into row objects.
 * Lenient by design (no strict date-window check) so the demo stays robust.
 * @param {string} csvText
 * @returns {{rows: Array, errors: string[]}}
 */
export function parseAndValidate(csvText) {
  const matrix = parseCsvRows(csvText);
  if (matrix.length === 0) {
    return { rows: [], errors: ['CSV is empty. Upload a file with a header row and data.'] };
  }

  const headers = matrix[0].map((h) => h.trim().toLowerCase());
  const missing = REQUIRED_COLUMNS.filter((c) => !headers.includes(c));
  if (missing.length) {
    return {
      rows: [],
      errors: [
        `Missing required column(s): ${missing.join(', ')}. ` +
        `Required columns are: ${REQUIRED_COLUMNS.join(', ')}.`,
      ],
    };
  }

  const idx = {};
  headers.forEach((h, i) => { idx[h] = i; });

  const rows = [];
  const errors = [];
  for (let r = 1; r < matrix.length; r++) {
    const cells = matrix[r];
    const get = (key) => (cells[idx[key]] || '').trim();

    const dateStr = get('date');
    const timeStr = get('time');
    const member = get('member');
    const eventType = get('event_type');
    const room = get('room');
    const devices = parseDevices(idx.devices !== undefined ? cells[idx.devices] : '');

    if (!(dateStr && timeStr && member && eventType && room)) {
      errors.push(`Row ${r + 1}: missing one or more required values.`);
      continue;
    }
    const minutes = parseTimeToMinutes(timeStr);
    if (minutes === null) {
      errors.push(`Row ${r + 1}: invalid time '${timeStr}' (expected HH:MM).`);
      continue;
    }
    rows.push({ date: dateStr, minutes, member, event_type: eventType, room, devices });
  }

  if (!rows.length && !errors.length) {
    errors.push('CSV contained a header but no data rows.');
  }
  return { rows, errors };
}

/**
 * Predict today's events from validated historical rows.
 * Groups by (member, event_type, room); averages time-of-day; confidence is
 * the fraction of analyzed days the routine appeared on.
 * @param {Array} rows
 * @returns {{predictions: Array, days_analyzed: number, rows_analyzed: number}}
 */
export function predict(rows) {
  const allDates = new Set(rows.map((r) => r.date));
  const totalDays = allDates.size || 1;

  const groups = new Map();
  for (const r of rows) {
    const key = `${r.member}||${r.event_type}||${r.room}`;
    if (!groups.has(key)) {
      groups.set(key, {
        member: r.member, event_type: r.event_type, room: r.room,
        dates: new Set(), minutes: [], devices: [],
      });
    }
    const g = groups.get(key);
    g.dates.add(r.date);
    g.minutes.push(r.minutes);
    for (const d of r.devices) if (!g.devices.includes(d)) g.devices.push(d);
  }

  const predictions = [];
  for (const g of groups.values()) {
    const daysObserved = g.dates.size;
    const avg = g.minutes.reduce((a, b) => a + b, 0) / g.minutes.length;
    const confidence = Math.round(Math.min(1, daysObserved / totalDays) * 100) / 100;
    predictions.push({
      member: g.member,
      event_type: g.event_type,
      room: g.room,
      devices: g.devices,
      predicted_time: minutesToHHMM(avg),
      predicted_minutes: Math.round(avg),
      confidence,
      days_observed: daysObserved,
    });
  }

  // Keep recurring routines (2+ distinct days); otherwise return everything.
  const recurring = predictions.filter((p) => p.days_observed >= 2);
  const chosen = recurring.length ? recurring : predictions;
  chosen.sort((a, b) => a.predicted_minutes - b.predicted_minutes || b.confidence - a.confidence);

  return { predictions: chosen, days_analyzed: totalDays, rows_analyzed: rows.length };
}

const norm = (s) => String(s || '').toLowerCase().trim();
function find(predictions, needles) {
  return predictions.filter((p) => needles.some((n) => norm(p.event_type).includes(n)));
}

/**
 * Turn learned routines into Alexa's anticipatory proactive actions.
 * Mirrors the EventScheduler-consumed shape (name, actionType, triggerTime,
 * targetDevice, category, room, reasoning, announcement, confidence).
 * @param {Array} predictions
 * @returns {Array}
 */
export function deriveProactiveActions(predictions) {
  const actions = [];
  const wakes = find(predictions, ['wake']);
  const leaves = find(predictions, ['leave', 'depart']);
  const arrivals = find(predictions, ['arrive', 'return', 'reach', 'back home']);
  const cooking = find(predictions, ['cook']);

  // 1. Geyser pre-heat — 45 min before the earliest wake-up.
  if (wakes.length) {
    const earliest = wakes.reduce((a, b) => (a.predicted_minutes <= b.predicted_minutes ? a : b));
    actions.push({
      name: 'Geyser Pre-heat',
      actionType: 'geyser_preheat',
      triggerTime: Math.max(0, earliest.predicted_minutes - 45),
      targetDevice: 'smart_geyser',
      category: 'utility',
      room: 'bath',
      confidence: earliest.confidence,
      reasoning: `${earliest.member} usually wakes around ${earliest.predicted_time}. Pre-heating water 45 minutes ahead ensures it's ready.`,
      announcement: {
        elder: 'Good morning! Hot water is ready for you.',
        parent: `Geyser warmed up — the family usually wakes around ${earliest.predicted_time}.`,
      },
    });
  }

  // 2. Security arm — when the last person leaves.
  if (leaves.length) {
    const lastLeave = leaves.reduce((a, b) => (a.predicted_minutes >= b.predicted_minutes ? a : b));
    actions.push({
      name: 'Security Arm',
      actionType: 'security_arm',
      triggerTime: lastLeave.predicted_minutes,
      targetDevice: 'smart_lock',
      category: 'security',
      room: 'balcony',
      confidence: lastLeave.confidence,
      reasoning: `The household typically leaves by ${lastLeave.predicted_time}. Arming the lock and camera once everyone is out.`,
      announcement: {
        elder: 'Security has been armed. You are safe inside.',
        parent: "Everyone's out — I've armed the lock and camera.",
      },
    });
  }

  // 3. Pre-cooling — 30 min before the earliest arrival home.
  if (arrivals.length) {
    const first = arrivals.reduce((a, b) => (a.predicted_minutes <= b.predicted_minutes ? a : b));
    actions.push({
      name: 'Pre-cooling Living Room',
      actionType: 'ac_precool',
      triggerTime: Math.max(0, first.predicted_minutes - 30),
      targetDevice: 'living_room_ac',
      category: 'climate',
      room: 'livingRoom',
      confidence: first.confidence,
      reasoning: `${first.member} usually arrives around ${first.predicted_time}. Pre-cooling 30 minutes ahead ensures a comfortable temperature on arrival.`,
      announcement: { parent: `Cooling the living room before ${first.member} gets home.` },
    });
  }

  // 4. Comfort lighting — 15 min before first evening activity (>= 17:00), else 17:45.
  const evening = predictions.filter((p) => p.predicted_minutes >= 17 * 60);
  let lightTrigger, lightConf, lightReason;
  if (evening.length) {
    const anchor = evening.reduce((a, b) => (a.predicted_minutes <= b.predicted_minutes ? a : b));
    lightTrigger = Math.max(0, anchor.predicted_minutes - 15);
    lightConf = anchor.confidence;
    lightReason = `Evening activity starts around ${anchor.predicted_time}. Transitioning to warm lighting for comfort.`;
  } else {
    lightTrigger = 17 * 60 + 45;
    lightConf = 0.75;
    lightReason = 'Sunset approaching. Transitioning to warm indoor lighting for comfort.';
  }
  actions.push({
    name: 'Comfort Lighting',
    actionType: 'comfort_lighting',
    triggerTime: lightTrigger,
    targetDevice: 'smart_lights',
    category: 'lighting',
    room: 'livingRoom',
    confidence: lightConf,
    reasoning: lightReason,
    announcement: { elder: 'Turning on warm lights for the evening.' },
  });

  // 5. Energy optimization — peak tariff window (14:00).
  const daytime = predictions.filter((p) => p.predicted_minutes >= 11 * 60 && p.predicted_minutes <= 17 * 60);
  if (daytime.length || cooking.length) {
    const pool = daytime.length ? daytime : predictions;
    const conf = Math.round((pool.reduce((a, p) => a + p.confidence, 0) / pool.length) * 100) / 100;
    actions.push({
      name: 'Energy Optimization',
      actionType: 'energy_optimization',
      triggerTime: 14 * 60,
      targetDevice: 'inverter_ups',
      category: 'power',
      room: 'utility',
      confidence: conf,
      reasoning: 'Peak electricity tariff begins around 14:00. Shifting non-essential loads to inverter backup to save cost.',
      announcement: { parent: 'Switched to inverter for non-essentials to save on peak tariff.' },
    });
  }

  actions.sort((a, b) => a.triggerTime - b.triggerTime);
  return actions;
}

/**
 * One-shot helper: CSV text → { predictions, proactive_actions, days_analyzed,
 * rows_analyzed, ai_enhanced, errors }. Shape mirrors the backend response so
 * callers can treat both paths uniformly.
 * @param {string} csvText
 */
export function predictFromCsv(csvText) {
  const { rows, errors } = parseAndValidate(csvText);
  if (errors.length && !rows.length) {
    return { predictions: [], proactive_actions: [], days_analyzed: 0, rows_analyzed: 0, ai_enhanced: false, errors };
  }
  const result = predict(rows);
  return {
    ...result,
    proactive_actions: deriveProactiveActions(result.predictions),
    ai_enhanced: false,
    errors: [],
  };
}
CSVPREDICT_EOF

echo "  -> src/data/sampleCsv.js"
cat > src/data/sampleCsv.js <<'SAMPLECSV_EOF'
/**
 * Sample activity-log CSV embedded as a string so the Learning Panel can
 * offer a "Download sample CSV" button without depending on a served file
 * path. Mirrors demo/sample_activity_log_family2.csv.
 */
export const SAMPLE_CSV_FILENAME = 'sample_activity_log.csv';

export const SAMPLE_CSV = `
date,time,member,event_type,room,devices
2026-06-15,05:42,Aarav,Wake up,Master Bedroom,Lights|Geyser
2026-06-15,06:02,Aarav,Morning jog,Balcony,Lights
2026-06-15,08:52,Aarav,Leave home,Balcony,Lock|Camera
2026-06-15,19:08,Aarav,Arrive home,Balcony,Lock|AC|Lights
2026-06-15,23:02,Aarav,Bedtime,Master Bedroom,AC|Lights
2026-06-15,06:28,Meera,Wake up,Master Bedroom,Lights
2026-06-15,07:28,Meera,Start cooking,Kitchen,Kitchen Hub|Lights
2026-06-15,10:03,Meera,Work from home,Study Room,Lights|AC|Echo
2026-06-15,14:05,Meera,Afternoon rest,Living Room,AC
2026-06-15,22:33,Meera,Bedtime,Master Bedroom,AC|Lights
2026-06-15,07:02,Kabir,Wake up,Kids Room,Lights
2026-06-15,10:01,Kabir,Online class,Study Room,Lights|AC|Echo
2026-06-15,17:12,Kabir,Gaming,Living Room,TV|Lights
2026-06-15,22:01,Kabir,Bedtime,Kids Room,Lights|AC
2026-06-16,05:48,Aarav,Wake up,Master Bedroom,Lights|Geyser
2026-06-16,06:05,Aarav,Morning jog,Balcony,Lights
2026-06-16,08:58,Aarav,Leave home,Balcony,Lock|Camera
2026-06-16,19:03,Aarav,Arrive home,Balcony,Lock|AC|Lights
2026-06-16,22:58,Aarav,Bedtime,Master Bedroom,AC|Lights
2026-06-16,06:33,Meera,Wake up,Master Bedroom,Lights
2026-06-16,07:33,Meera,Start cooking,Kitchen,Kitchen Hub|Lights
2026-06-16,09:58,Meera,Work from home,Study Room,Lights|AC|Echo
2026-06-16,13:58,Meera,Afternoon rest,Living Room,AC
2026-06-16,22:28,Meera,Bedtime,Master Bedroom,AC|Lights
2026-06-16,06:58,Kabir,Wake up,Kids Room,Lights
2026-06-16,09:59,Kabir,Online class,Study Room,Lights|AC|Echo
2026-06-16,17:18,Kabir,Gaming,Living Room,TV|Lights
2026-06-16,21:58,Kabir,Bedtime,Kids Room,Lights|AC
2026-06-17,05:44,Aarav,Wake up,Master Bedroom,Lights|Geyser
2026-06-17,05:59,Aarav,Morning jog,Balcony,Lights
2026-06-17,08:55,Aarav,Leave home,Balcony,Lock|Camera
2026-06-17,19:12,Aarav,Arrive home,Balcony,Lock|AC|Lights
2026-06-17,23:05,Aarav,Bedtime,Master Bedroom,AC|Lights
2026-06-17,06:30,Meera,Wake up,Master Bedroom,Lights
2026-06-17,07:30,Meera,Start cooking,Kitchen,Kitchen Hub|Lights
2026-06-17,10:05,Meera,Work from home,Study Room,Lights|AC|Echo
2026-06-17,14:02,Meera,Afternoon rest,Living Room,AC
2026-06-17,22:31,Meera,Bedtime,Master Bedroom,AC|Lights
2026-06-17,07:05,Kabir,Wake up,Kids Room,Lights
2026-06-17,10:02,Kabir,Online class,Study Room,Lights|AC|Echo
2026-06-17,17:08,Kabir,Gaming,Living Room,TV|Lights
2026-06-17,22:04,Kabir,Bedtime,Kids Room,Lights|AC
2026-06-18,05:46,Aarav,Wake up,Master Bedroom,Lights|Geyser
2026-06-18,06:03,Aarav,Morning jog,Balcony,Lights
2026-06-18,08:50,Aarav,Leave home,Balcony,Lock|Camera
2026-06-18,18:58,Aarav,Arrive home,Balcony,Lock|AC|Lights
2026-06-18,23:00,Aarav,Bedtime,Master Bedroom,AC|Lights
2026-06-18,06:31,Meera,Wake up,Master Bedroom,Lights
2026-06-18,07:27,Meera,Start cooking,Kitchen,Kitchen Hub|Lights
2026-06-18,10:00,Meera,Work from home,Study Room,Lights|AC|Echo
2026-06-18,14:00,Meera,Afternoon rest,Living Room,AC
2026-06-18,22:30,Meera,Bedtime,Master Bedroom,AC|Lights
2026-06-18,07:00,Kabir,Wake up,Kids Room,Lights
2026-06-18,10:00,Kabir,Online class,Study Room,Lights|AC|Echo
2026-06-18,17:15,Kabir,Gaming,Living Room,TV|Lights
2026-06-18,22:00,Kabir,Bedtime,Kids Room,Lights|AC
`;
SAMPLECSV_EOF

echo "  -> src/ui/LearningPanel.js"
cat > src/ui/LearningPanel.js <<'LEARNINGPANEL_EOF'
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
LEARNINGPANEL_EOF

echo "  -> src/main.js"
cat > src/main.js <<'MAINJS_EOF'
/**
 * Alexa Thinks Ahead — 2D Interactive Demo
 * Entry point: bootstraps all modules, wires connections, and starts the app.
 *
 * Requirements: 3.3, 7.1, 8.2
 */

// ─── Scene Module (2D Floor Plan) ────────────────────────────────
import { FloorPlan2D } from './scene/FloorPlan2D.js';

// ─── Simulation Modules ──────────────────────────────────────────
import { SimulationEngine } from './simulation/SimulationEngine.js';
import { StateStore } from './simulation/StateStore.js';
import { EventScheduler } from './simulation/EventScheduler.js';
import { PROACTIVE_ACTIONS } from './simulation/ProactiveActions.js';
import { PowerCutScenario } from './simulation/PowerCutScenario.js';

// ─── Data Layer ──────────────────────────────────────────────────
import { DataLayer } from './data/DataLayer.js';

// ─── UI Modules ──────────────────────────────────────────────────
import { UIManager } from './ui/UIManager.js';
import { LearningPanel } from './ui/LearningPanel.js';
import { DeploymentPanel } from './ui/DeploymentPanel.js';
import { EventLog } from './ui/EventLog.js';
import { TrustGauges } from './ui/TrustGauges.js';
import { ReasoningPanel } from './ui/ReasoningPanel.js';

// ─── Utilities ───────────────────────────────────────────────────
import { eventBus, EVENTS } from './utils/eventBus.js';

// ═══════════════════════════════════════════════════════════════════
// Bootstrap
// ═══════════════════════════════════════════════════════════════════

// --- Core instances ---
const simulationEngine = new SimulationEngine();
const stateStore = new StateStore();
const dataLayer = new DataLayer();

// --- 2D Floor Plan setup ---
const floorPlan = new FloorPlan2D(document.getElementById('3d-container'));

// --- UI setup ---
const uiManager = new UIManager(stateStore, simulationEngine);
const learningPanel = new LearningPanel(uiManager, eventBus, dataLayer);
const deploymentPanel = new DeploymentPanel(uiManager, simulationEngine);
const eventLog = new EventLog(stateStore);
const trustGauges = new TrustGauges(stateStore);

// --- Event Scheduler ---
const eventScheduler = new EventScheduler(simulationEngine, stateStore);
eventScheduler.loadActions(PROACTIVE_ACTIONS);

// --- Reasoning Panel ---
const reasoningPanel = new ReasoningPanel();

// --- Power Cut Scenario ---
// FloorPlan2D exposes the same interface as Effects + SpeechBubbleManager + DeviceIndicators
const powerCutScenario = new PowerCutScenario(
  floorPlan,        // effects (has highlightDevice, powerCutFlicker, inverterGlow, dimRooms, restoreRooms)
  floorPlan,        // speechBubbles (has show → we adapt below)
  stateStore,
  eventBus,
  reasoningPanel,
  floorPlan          // deviceIndicators (has getDevicePosition, getMesh)
);

// Monkey-patch speechBubbles.show to use floorPlan.showSpeechBubble
// PowerCutScenario calls: this.speechBubbles.show(position, text, duration)
// FloorPlan2D expects: showSpeechBubble(deviceId, text, duration)
// We provide a compatibility adapter:
const originalTrigger = powerCutScenario.trigger.bind(powerCutScenario);
powerCutScenario._originalSpeechBubblesShow = powerCutScenario.speechBubbles.show;

// Override the _executeExplain to use device-based speech bubbles
const originalExplain = powerCutScenario._executeExplain.bind(powerCutScenario);
powerCutScenario._executeExplain = function (currentTimeMinutes) {
  // Speech bubble at study_room echo for Arjun
  floorPlan.showSpeechBubble(
    'echo_study',
    "Power cut detected. Your study room is on backup power — your class won't be interrupted, Arjun.",
    6000
  );

  // Speech bubble at living_room echo for Dadaji
  floorPlan.showSpeechBubble(
    'echo_living',
    "Don't worry, Dadaji. Living room lights and fan are running on inverter.",
    6000
  );

  // Speech bubble at kitchen for Priya
  floorPlan.showSpeechBubble(
    'kitchen_hub',
    "Priya, I've paused the kitchen hub to conserve inverter. Estimated backup: 2.5 hours.",
    6000
  );

  // Log EXPLAIN stage
  this.stateStore.addEventLogEntry({
    time: currentTimeMinutes,
    action: 'Power Cut - EXPLAIN',
    device: 'echo_devices',
    reasoning: 'Announcing status to all family members.',
    type: 'power_cut',
    stage: 'EXPLAIN',
  });
};

// Override _executeAct to use FloorPlan2D methods
const originalAct = powerCutScenario._executeAct.bind(powerCutScenario);
powerCutScenario._executeAct = function (currentTimeMinutes) {
  // Visual: Inverter glow (green)
  floorPlan.inverterGlow('inverter_ups');

  // Visual: Dim all rooms except study_room and living_room
  floorPlan.dimRooms(['study_room', 'living_room']);

  // Log ACT stage
  this.stateStore.addEventLogEntry({
    time: currentTimeMinutes,
    action: 'Power Cut - ACT',
    device: 'inverter_ups',
    reasoning: 'AC OFF, Geyser OFF, Study lights → battery mode',
    type: 'power_cut',
    stage: 'ACT',
  });
};

// Override restore to use FloorPlan2D
const originalRestore = powerCutScenario.restore.bind(powerCutScenario);
powerCutScenario.restore = function () {
  // Clear any pending timers
  this.activeTimers.forEach((timer) => clearTimeout(timer));
  this.activeTimers = [];

  if (this._autoRestoreTimer !== null) {
    clearTimeout(this._autoRestoreTimer);
    this._autoRestoreTimer = null;
  }

  // Restore all room lighting effects
  floorPlan.restoreAll();

  // Hide reasoning panel
  this.reasoningPanel.hide();

  // Emit power restore event
  this.eventBus.emit(EVENTS.POWER_RESTORE, {});
};

// ═══════════════════════════════════════════════════════════════════
// Wire Connections
// ═══════════════════════════════════════════════════════════════════

// 1. Simulation tick → Floor Plan updates
simulationEngine.onTick((timeMinutes) => {
  floorPlan.updateAvatars(timeMinutes);
  floorPlan.updateLighting(timeMinutes);
});

// 2. Proactive action events → FloorPlan highlight + speech bubbles
eventBus.on(EVENTS.PROACTIVE_ACTION, (payload) => {
  // Highlight the target device with a glow pulse
  floorPlan.highlightDevice(payload.targetDevice);

  // Show speech bubble with the action's announcement
  const announcement = payload.announcement;
  const text = announcement
    ? announcement.parent || announcement.elder || announcement.child || payload.name
    : payload.name;

  floorPlan.showSpeechBubble(payload.targetDevice, text, 5000);
});

// 2b. On Deploy: if a CSV produced proactive actions, replace the hardcoded
//     defaults so the simulation is driven by the uploaded household data.
eventBus.on(EVENTS.PHASE_CHANGE, (payload) => {
  if (
    payload &&
    payload.phase === 'deployment' &&
    Array.isArray(payload.proactiveActions) &&
    payload.proactiveActions.length > 0
  ) {
    eventScheduler.loadActions(payload.proactiveActions);
    console.log(
      `Loaded ${payload.proactiveActions.length} CSV-derived proactive actions into the scheduler.`
    );
  }
});

// 3. Data mode toggle button
const dataToggleContainer = document.getElementById('data-toggle');
if (dataToggleContainer) {
  dataToggleContainer.innerHTML = `
    <div class="data-toggle-inner">
      <span class="data-toggle-label">Data Mode:</span>
      <button id="data-mode-btn" class="btn-accent data-mode-btn">
        Mock
      </button>
    </div>
  `;

  const dataModeBtn = document.getElementById('data-mode-btn');
  dataModeBtn.addEventListener('click', () => {
    const newMode = dataLayer.mode === 'mock' ? 'real' : 'mock';
    dataLayer.setMode(newMode);
    dataModeBtn.textContent = newMode === 'mock' ? 'Mock' : 'Real';
    dataModeBtn.classList.toggle('data-mode-real', newMode === 'real');
  });
}

// Helper: resolve a device ID to its room for the real-mode power-cut animation.
// Uses known device-to-room mappings from DEVICE_PLACEMENTS in FloorPlan2D.
const DEVICE_ROOM_MAP = {
  living_room_ac: 'living_room',
  smart_tv: 'living_room',
  echo_living: 'living_room',
  kitchen_hub: 'kitchen',
  water_purifier: 'kitchen',
  security_camera: 'balcony',
  smart_lock: 'balcony',
  smart_geyser: 'bath',
  inverter_ups: 'kitchen',
  echo_study: 'study_room',
  echo_kids: 'kids_room',
};
function _getDevicePlacement(deviceId) {
  return DEVICE_ROOM_MAP[deviceId] || null;
}

// 4. Power Cut button — wire the button rendered inside the timeline panel
const powerCutBtn = document.getElementById('power-cut-btn');
if (powerCutBtn) {
  powerCutBtn.addEventListener('click', async () => {
    const currentTimeMinutes = simulationEngine.currentTimeMinutes;

    // In real mode: call the backend scenario endpoint and animate from the response
    if (dataLayer.mode === 'real') {
      try {
        const response = await dataLayer.apiProvider.runPowerCutScenario();

        // --- Stage 1: SENSE (flicker effect) ---
        floorPlan.powerCutFlicker();
        stateStore.addEventLogEntry({
          time: currentTimeMinutes,
          action: 'Power Cut - SENSE',
          device: 'inverter_ups',
          reasoning: 'Power grid failure detected (real backend).',
          type: 'power_cut',
          stage: 'SENSE',
        });

        // --- Stage 2: THINK (show reasoning/explanation) ---
        setTimeout(() => {
          // Render the explanation and reasoning chain in the ReasoningPanel
          const reasoningContent = `
            <h3>⚡ Power Cut — Alexa's Reasoning (Live)</h3>
            <div class="reasoning-steps">
              <p>💬 <strong>Explanation:</strong> ${response.explanation || 'Analyzing situation...'}</p>
              ${response.reasoning_chain ? `<p>🧠 <strong>Reasoning:</strong> ${response.reasoning_chain}</p>` : ''}
            </div>
          `;
          reasoningPanel.show(reasoningContent);

          stateStore.addEventLogEntry({
            time: currentTimeMinutes,
            action: 'Power Cut - THINK',
            device: 'inverter_ups',
            reasoning: response.explanation || 'Contextual reasoning from backend.',
            type: 'power_cut',
            stage: 'THINK',
          });
        }, 500);

        // --- Stage 3: ACT (map target_devices to FloorPlan2D effects) ---
        setTimeout(() => {
          const roomsToKeepLit = [];

          for (const action of response.actions) {
            // Log each action to the EventLog
            stateStore.addEventLogEntry({
              time: currentTimeMinutes,
              action: `Power Cut - ACT: ${action.strategy}`,
              device: (action.target_devices || []).join(', '),
              reasoning: action.reasoning || `Strategy: ${action.strategy}, Confidence: ${action.confidence}`,
              type: 'power_cut',
              stage: 'ACT',
            });

            // Map target_devices to visual effects
            for (const deviceId of action.target_devices || []) {
              if (deviceId === 'inverter_ups') {
                floorPlan.inverterGlow(deviceId);
              } else {
                floorPlan.highlightDevice(deviceId, 3000);
              }

              // Track rooms that should stay lit (devices with power priority)
              if (action.strategy === 'energy_optimization' || action.strategy === 'priority_power') {
                const placement = _getDevicePlacement(deviceId);
                if (placement && !roomsToKeepLit.includes(placement)) {
                  roomsToKeepLit.push(placement);
                }
              }
            }
          }

          // Dim rooms — keep priority rooms lit
          const defaultPriorityRooms = ['study_room', 'living_room'];
          floorPlan.dimRooms(roomsToKeepLit.length > 0 ? roomsToKeepLit : defaultPriorityRooms);
        }, 1500);

        // --- Stage 4: EXPLAIN (speech bubbles with family-facing lines) ---
        setTimeout(() => {
          // Show explanation text as speech bubble on echo devices
          if (response.explanation) {
            floorPlan.showSpeechBubble('echo_living', response.explanation, 7000);
          }

          // Surface family-facing lines for specific members
          floorPlan.showSpeechBubble(
            'echo_study',
            "Your class won't be interrupted, Arjun. Study room is on backup power.",
            6000
          );
          floorPlan.showSpeechBubble(
            'kitchen_hub',
            "Kitchen hub paused to conserve inverter. Estimated backup: 2.5 hours.",
            6000
          );

          stateStore.addEventLogEntry({
            time: currentTimeMinutes,
            action: 'Power Cut - EXPLAIN',
            device: 'echo_devices',
            reasoning: response.explanation || 'Announcing status to family.',
            type: 'power_cut',
            stage: 'EXPLAIN',
          });
        }, 2500);

        // Auto-restore after 30 seconds
        setTimeout(() => {
          floorPlan.restoreAll();
          reasoningPanel.hide();
        }, 30000);

      } catch (err) {
        console.error('Real power-cut scenario failed, falling back to scripted:', err);
        // Show error indication in event log
        stateStore.addEventLogEntry({
          time: currentTimeMinutes,
          action: 'Power Cut - ERROR',
          device: 'system',
          reasoning: `Backend scenario failed: ${err.message}. Falling back to scripted demo.`,
          type: 'error',
          stage: 'ERROR',
        });
        // Fall back to scripted scenario
        powerCutScenario.trigger(currentTimeMinutes);
      }
    } else {
      // Mock mode: run existing scripted PowerCutScenario unchanged
      powerCutScenario.trigger(currentTimeMinutes);
    }
  });
}

// 5. Initialize trust gauges with mock data
dataLayer.getAutonomyTiers().then((tiersData) => {
  if (trustGauges.initializeFromData) {
    trustGauges.initializeFromData(tiersData);
  }
}).catch((err) => {
  console.warn('Failed to initialize trust gauges:', err);
});

// ═══════════════════════════════════════════════════════════════════
// Ready
// ═══════════════════════════════════════════════════════════════════
console.log('Alexa Thinks Ahead 2D Demo — all modules wired and ready.');

// Suppress unused variable warnings — these modules self-register via constructors
void learningPanel;
void deploymentPanel;
void eventLog;
MAINJS_EOF

echo "  -> src/data/ApiProvider.js"
cat > src/data/ApiProvider.js <<'APIPROVIDER_EOF'
/**
 * Read a Vite env var when running in a bundled context. Falls back to the
 * provided default in tests / non-Vite environments where import.meta.env
 * is undefined.
 */
function envValue(key, fallback) {
  try {
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env[key] !== undefined) {
      return import.meta.env[key];
    }
  } catch (_) {
    // import.meta not available (e.g. CommonJS test runner) — use fallback.
  }
  return fallback;
}

/**
 * ApiProvider - HTTP client for the real backend.
 *
 * Local demo (default):   baseUrl http://localhost:8080, prefix /api/v1
 * AWS API Gateway:        set VITE_API_BASE_URL to the stage URL
 *                         (e.g. https://abc123.execute-api.ap-south-1.amazonaws.com/dev)
 *                         and VITE_API_PREFIX to '' since the gateway routes
 *                         are mounted at the stage root (/devices, /context/...).
 * Optional auth:          set VITE_API_AUTH_TOKEN to send a Bearer token
 *                         (required when the API Gateway JWT authorizer is on).
 *
 * Implements the same interface as MockProvider so DataLayer can
 * delegate calls transparently.
 */
export class ApiProvider {
  /**
   * @param {string} [baseUrl] - Backend base URL. Defaults to VITE_API_BASE_URL
   *   or http://localhost:8080.
   * @param {object} [options]
   * @param {string} [options.apiPrefix] - Path prefix prepended to every route.
   *   Defaults to VITE_API_PREFIX or '/api/v1'. Use '' for API Gateway.
   * @param {string} [options.authToken] - Optional Bearer token. Defaults to
   *   VITE_API_AUTH_TOKEN.
   */
  constructor(baseUrl, options = {}) {
    this.baseUrl = baseUrl ?? envValue('VITE_API_BASE_URL', 'http://localhost:8080');
    this.apiPrefix = options.apiPrefix ?? envValue('VITE_API_PREFIX', '/api/v1');
    this.authToken = options.authToken ?? envValue('VITE_API_AUTH_TOKEN', null);
  }

  /**
   * Private helper that handles all HTTP communication.
   * @param {string} method - HTTP method (GET, POST, PUT)
   * @param {string} path - API path relative to the prefix (e.g. /devices)
   * @param {object|null} body - Request body for POST/PUT requests
   * @returns {Promise<object>} Parsed JSON response
   * @throws {Error} When the response status is not ok
   */
  async request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }
    const options = { method, headers };
    if (body) {
      options.body = JSON.stringify(body);
    }
    const response = await fetch(`${this.baseUrl}${this.apiPrefix}${path}`, options);
    if (!response.ok) {
      // Try to surface the backend's structured error (message + details).
      let payload = null;
      try {
        payload = await response.json();
      } catch (_) {
        // non-JSON error body
      }
      const err = new Error(
        (payload && payload.error) ? payload.error : `API error: ${response.status}`
      );
      err.status = response.status;
      if (payload && payload.details) {
        err.details = payload.details;
      }
      throw err;
    }
    return response.json();
  }

  /**
   * Fetch all registered devices.
   * Normalizes response to match MockProvider shape: {devices: [...], count: N}
   * @returns {Promise<{devices: Array, count: number}>}
   */
  async getDevices() {
    const data = await this.request('GET', '/devices');
    return {
      devices: data.devices ?? [],
      count: data.count ?? (data.devices?.length ?? 0),
    };
  }

  /**
   * Fetch current state of a specific device.
   * Returns the device entry object directly (matching MockProvider shape).
   * @param {string} id - Device identifier
   * @returns {Promise<object>}
   */
  async getDeviceState(id) {
    const data = await this.request('GET', `/devices/${id}/state`);
    // Backend returns the device entry object directly; pass through as-is
    return data;
  }

  /**
   * Send a command to a specific device.
   * @param {string} id - Device identifier
   * @param {object} command - Command payload
   * @returns {Promise<object>}
   */
  async sendCommand(id, command) {
    return this.request('POST', `/devices/${id}/command`, command);
  }

  /**
   * Fetch the current unified home context snapshot.
   * Normalizes response to match MockProvider shape:
   * {timestamp, deviceStates: [...], activeActivities: [...], environmentals: {...}}
   * @returns {Promise<object>}
   */
  async getContextSnapshot() {
    const data = await this.request('GET', '/context/snapshot');
    return {
      timestamp: data.timestamp,
      deviceStates: data.deviceStates ?? [],
      activeActivities: data.activeActivities ?? [],
      environmentals: data.environmentals ?? { temperature: 0, humidity: 0, powerGrid: 'unknown' },
    };
  }

  /**
   * Fetch detected temporal patterns.
   * Normalizes response to match MockProvider shape: {patterns: [...]}
   * @returns {Promise<{patterns: Array}>}
   */
  async getPatterns() {
    const data = await this.request('GET', '/context/patterns');
    return { patterns: data.patterns ?? [] };
  }

  /**
   * Fetch autonomy tier configuration for all device categories.
   * Normalizes response to match MockProvider shape: {tiers: [...]}
   * @returns {Promise<{tiers: Array}>}
   */
  async getAutonomyTiers() {
    const data = await this.request('GET', '/autonomy/tiers');
    return { tiers: data.tiers ?? [] };
  }

  /**
   * Update autonomy tier configuration for a specific device category.
   * @param {string} device - Device category identifier
   * @param {object} config - New tier configuration
   * @returns {Promise<object>}
   */
  async updateTier(device, config) {
    return this.request('PUT', `/autonomy/tiers/${device}`, config);
  }

  /**
   * Trigger the live power-cut scenario on the backend.
   * POST /api/v1/scenario/power-cut
   * @returns {Promise<{actions: Array, explanation: string, reasoning_chain: string}>}
   */
  async runPowerCutScenario() {
    return this.request('POST', '/scenario/power-cut', {});
  }

  /**
   * Upload a CSV of the previous week's activity log and get predicted
   * events for today. The backend validates the CSV format first.
   * @param {string} csvText - Raw CSV file content.
   * @returns {Promise<{predictions: Array, days_analyzed: number, rows_analyzed: number}>}
   */
  async predictEventsFromCsv(csvText) {
    return this.request('POST', '/predict/events', { csv: csvText });
  }
}
APIPROVIDER_EOF

echo "  -> src/data/DataLayer.js"
cat > src/data/DataLayer.js <<'DATALAYER_EOF'
/**
 * DataLayer - Unified data access layer with mode toggle.
 * Delegates all calls to either MockProvider (offline) or ApiProvider (live backend).
 * Defaults to 'mock' mode on initialization.
 */
import { MockProvider } from './MockProvider.js';
import { ApiProvider } from './ApiProvider.js';

export class DataLayer {
  constructor() {
    /** @type {'mock' | 'real'} */
    this.mode = 'mock';
    this.mockProvider = new MockProvider();
    this.apiProvider = new ApiProvider();
  }

  /**
   * Returns the active provider based on the current mode.
   * @returns {MockProvider | ApiProvider}
   */
  get provider() {
    return this.mode === 'real' ? this.apiProvider : this.mockProvider;
  }

  /**
   * Switch between 'mock' and 'real' data modes.
   * @param {'mock' | 'real'} mode
   */
  setMode(mode) {
    this.mode = mode;
  }

  /**
   * Fetch all registered devices.
   * @returns {Promise<{devices: Array, count: number}>}
   */
  async getDevices() {
    return this.provider.getDevices();
  }

  /**
   * Fetch current state of a specific device.
   * @param {string} id - Device identifier
   * @returns {Promise<object>}
   */
  async getDeviceState(id) {
    return this.provider.getDeviceState(id);
  }

  /**
   * Send a command to a specific device.
   * @param {string} id - Device identifier
   * @param {object} command - Command payload
   * @returns {Promise<object>}
   */
  async sendCommand(id, command) {
    return this.provider.sendCommand(id, command);
  }

  /**
   * Fetch the current unified home context snapshot.
   * @returns {Promise<object>}
   */
  async getContextSnapshot() {
    return this.provider.getContextSnapshot();
  }

  /**
   * Fetch detected temporal patterns.
   * @returns {Promise<{patterns: Array}>}
   */
  async getPatterns() {
    return this.provider.getPatterns();
  }

  /**
   * Fetch autonomy tier configuration for all device categories.
   * @returns {Promise<{tiers: Array}>}
   */
  async getAutonomyTiers() {
    return this.provider.getAutonomyTiers();
  }

  /**
   * Update autonomy tier configuration for a specific device category.
   * @param {string} device - Device category identifier
   * @param {object} config - New tier configuration
   * @returns {Promise<object>}
   */
  async updateTier(device, config) {
    return this.provider.updateTier(device, config);
  }
}
DATALAYER_EOF

echo "  -> src/simulation/EventScheduler.js"
cat > src/simulation/EventScheduler.js <<'EVENTSCHED_EOF'
/**
 * EventScheduler — evaluates scheduled proactive actions against the
 * current simulation time and fires events when triggers are met.
 *
 * Registers itself on the SimulationEngine tick loop and checks each
 * action's triggerTime on every frame. Once fired, an action is not
 * repeated (one-shot per simulation run).
 *
 * Requirements: 8.1, 8.3, 9.2
 */
import { eventBus, EVENTS } from '../utils/eventBus.js';

export class EventScheduler {
  /**
   * @param {import('./SimulationEngine.js').SimulationEngine} simulationEngine
   * @param {import('./StateStore.js').StateStore} stateStore
   * @param {import('../utils/eventBus.js').eventBus} bus
   */
  constructor(simulationEngine, stateStore, bus = eventBus) {
    this.simulation = simulationEngine;
    this.store = stateStore;
    this.bus = bus;

    /** @type {Array<object>} Loaded proactive action definitions */
    this.scheduledActions = [];

    /** @type {Set<string>} IDs of actions already fired this run */
    this.firedActions = new Set();

    // Register on simulation tick
    this.simulation.onTick((time) => this.evaluate(time));
  }

  /**
   * Load a set of proactive actions into the scheduler.
   * Assigns unique IDs and clears the fired tracking set.
   * @param {Array<object>} actions — action definitions from ProactiveActions
   */
  loadActions(actions) {
    this.scheduledActions = actions.map((a) => ({
      ...a,
      id: a.id || ('act-' + Date.now() + '-' + Math.random().toString(36).slice(2)),
    }));
    this.firedActions.clear();
  }

  /**
   * Evaluate all scheduled actions against the current simulation time.
   * Fires each action at most once when currentTime >= triggerTime.
   * @param {number} currentTimeMinutes — simulation time in minutes (0–1439)
   */
  evaluate(currentTimeMinutes) {
    for (const action of this.scheduledActions) {
      if (this.firedActions.has(action.id)) continue;

      if (currentTimeMinutes >= action.triggerTime) {
        this.firedActions.add(action.id);

        // Emit proactive action event via eventBus
        this.bus.emit(EVENTS.PROACTIVE_ACTION, {
          ...action,
          timestamp: currentTimeMinutes,
        });

        // Add entry to the event log in StateStore
        this.store.addEventLogEntry({
          time: currentTimeMinutes,
          action: action.name,
          device: action.targetDevice,
          reasoning: action.reasoning,
          type: action.actionType,
        });

        // Increase trust score for the action's category (+3 per action)
        this.store.updateTrustScore(action.category, 3);
      }
    }
  }
}
EVENTSCHED_EOF

echo "  -> src/styles/panels.css"
cat > src/styles/panels.css <<'PANELSCSS_EOF'
/* ============================================
   Panel Layout Styles - Alexa Thinks Ahead
   ============================================ */

/* ---- Learning Phase Layout ---- */

#learning-phase {
  position: fixed;
  top: 0;
  left: 0;
  width: 30%;
  height: 100%;
  z-index: 10;
  padding: 1.5rem;
  transform: translateX(0);
  transition: opacity 0.3s ease,
              visibility 0.3s ease,
              transform 0.3s ease;
}

#learning-phase .panel-content {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* ---- Brand Header ---- */
.brand-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid rgba(0, 202, 255, 0.12);
}

.brand-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  font-size: 0.6rem;
  color: #fff;
  background: radial-gradient(circle at 30% 30%, #36d3ff, #0091b3);
  box-shadow: 0 0 14px rgba(0, 202, 255, 0.5);
  flex-shrink: 0;
}

.brand-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text, #e6edf3);
  letter-spacing: 0.01em;
}

.brand-subtitle {
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--color-accent, #00CAFF);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

#event-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

#event-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

#deploy-btn {
  margin-top: auto;
  flex-shrink: 0;
}

/* ---- Deployment Phase Layout ---- */

#deployment-phase {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
  opacity: 1;
  visibility: visible;
  transition: opacity 0.3s ease,
              visibility 0.3s ease;
}

#deployment-phase > * {
  pointer-events: auto;
}

/* Timeline Panel - Fixed bottom */
#timeline-panel {
  position: fixed;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  width: min(96%, 920px);
  padding: 0.85rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  z-index: 20;
}

.timeline-controls {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  width: 100%;
}

.timeline-play-btn {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  padding: 0;
  font-size: 0.9rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.speed-controls-group {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.speed-label {
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--color-text-muted, #8b949e);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-right: 0.15rem;
}

.btn-power-cut {
  margin-left: auto;
  flex-shrink: 0;
  font-family: var(--font-family, 'Inter', sans-serif);
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  cursor: pointer;
  color: #ffd76a;
  background: rgba(255, 180, 0, 0.12);
  border: 1px solid rgba(255, 180, 0, 0.4);
  transition: background 0.15s ease, box-shadow 0.15s ease;
}

.btn-power-cut:hover {
  background: rgba(255, 180, 0, 0.22);
  box-shadow: 0 0 14px rgba(255, 180, 0, 0.3);
}

.timeline-scrubber-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.timeline-scrubber-wrapper .timeline-scrubber {
  width: 100%;
}

.scrubber-markers {
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: 0 2px;
}

.scrubber-markers span {
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--color-text-muted, #8b949e);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}

/* Event Log Panel - Fixed right sidebar */
#event-log-panel {
  position: fixed;
  top: 1rem;
  right: 1rem;
  width: 320px;
  max-height: calc(100vh - 8.5rem);
  overflow-y: auto;
  padding: 1.25rem;
  z-index: 15;
}

/* Trust Gauges - Fixed top-left overlay */
#trust-gauges {
  position: fixed;
  top: 1rem;
  left: 1rem;
  width: 240px;
  max-height: calc(100vh - 8.5rem);
  overflow-y: auto;
  padding: 1rem;
  z-index: 15;
}

/* Speed Button */
.speed-btn {
  font-family: var(--font-family, 'Inter', sans-serif);
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.4rem 0.75rem;
  background: rgba(13, 17, 23, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--color-border, rgba(0, 202, 255, 0.15));
  border-radius: 6px;
  color: var(--color-text-muted, #8b949e);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  outline: none;
}

.speed-btn:hover {
  background: rgba(0, 202, 255, 0.1);
  color: var(--color-accent, #00CAFF);
  border-color: rgba(0, 202, 255, 0.3);
}

.speed-btn.active {
  background: rgba(0, 202, 255, 0.15);
  color: var(--color-accent, #00CAFF);
  border-color: var(--color-accent, #00CAFF);
  box-shadow: 0 0 8px rgba(0, 202, 255, 0.2);
}

/* Timeline Scrubber */
.timeline-scrubber {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  border: none;
  outline: none;
  cursor: pointer;
  padding: 0;
}

.timeline-scrubber::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  background: var(--color-accent, #00CAFF);
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 6px rgba(0, 202, 255, 0.4);
  cursor: grab;
  transition: transform 0.1s ease, box-shadow 0.1s ease;
}

.timeline-scrubber::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 0 10px rgba(0, 202, 255, 0.6);
}

.timeline-scrubber::-moz-range-thumb {
  width: 14px;
  height: 14px;
  background: var(--color-accent, #00CAFF);
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 6px rgba(0, 202, 255, 0.4);
  cursor: grab;
}

.timeline-scrubber::-webkit-slider-runnable-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.timeline-scrubber::-moz-range-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

/* Time Display */
.time-display {
  font-family: 'Inter', monospace;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-accent, #00CAFF);
  min-width: 3.5rem;
  text-align: center;
  letter-spacing: 0.05em;
}

/* Reasoning Panel - Center overlay (glassmorphism) */
#reasoning-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: min(90%, 500px);
  max-height: 80vh;
  overflow-y: auto;
  z-index: 900;
  pointer-events: none;
  transition: opacity 0.4s ease, visibility 0.4s ease;
}

#reasoning-panel.hidden {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
}

#reasoning-panel.visible {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.reasoning-content {
  padding: 1.75rem;
}

.reasoning-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.reasoning-icon {
  font-size: 1.5rem;
}

.reasoning-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text, #e6edf3);
}

.reasoning-stage-label {
  display: inline-block;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #00FF88;
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.25);
  border-radius: 4px;
  padding: 0.2rem 0.6rem;
  margin-bottom: 1rem;
}

.reasoning-section {
  margin-bottom: 1rem;
}

.reasoning-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-accent, #00CAFF);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.reasoning-context-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.reasoning-context-list li {
  font-size: 0.8rem;
  color: var(--color-text, #e6edf3);
  padding: 0.3rem 0.6rem;
  background: rgba(0, 202, 255, 0.04);
  border-radius: 4px;
  border-left: 2px solid rgba(0, 202, 255, 0.3);
}

.reasoning-priority-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.reasoning-priority-col {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.reasoning-col-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-text-muted, #8b949e);
  margin-bottom: 0.25rem;
}

.reasoning-priority-col ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.reasoning-keep {
  font-size: 0.75rem;
  color: #00FF88;
}

.reasoning-shed {
  font-size: 0.75rem;
  color: #ff6b6b;
}

.reasoning-duration {
  background: rgba(0, 202, 255, 0.06);
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  border: 1px solid rgba(0, 202, 255, 0.12);
}

.reasoning-duration span {
  font-size: 0.8rem;
  color: var(--color-text, #e6edf3);
}

.reasoning-duration strong {
  color: var(--color-accent, #00CAFF);
}

/* Data Mode Toggle */
#data-toggle {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  z-index: 20;
}

/* ---- Speech Bubble (3D Overlay) ---- */

.speech-bubble {
  backdrop-filter: blur(var(--blur-amount, 12px));
  -webkit-backdrop-filter: blur(var(--blur-amount, 12px));
  background: var(--color-bg-panel, rgba(13, 17, 23, 0.7));
  border: 1px solid var(--color-border, rgba(0, 202, 255, 0.15));
  border-radius: 10px;
  padding: 0.75rem 1rem;
  max-width: 260px;
  font-family: var(--font-family, 'Inter', sans-serif);
  font-size: 0.8rem;
  color: var(--color-text, #e6edf3);
  line-height: 1.4;
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  pointer-events: none;
  transition: opacity 0.5s ease;
}

/* Fade-out animation class */
.fade-out {
  opacity: 0;
  transition: opacity 0.5s ease;
}

/* ---- Trust Gauges Component ---- */

.trust-gauges-title {
  margin: 0 0 0.75rem 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-accent, #00CAFF);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.trust-gauges-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.trust-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.trust-gauge svg {
  display: block;
}

.gauge-category-name {
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--color-text-muted, #8b949e);
  text-transform: capitalize;
  text-align: center;
}

.gauge-tier {
  font-size: 0.6rem;
  font-weight: 600;
  color: var(--color-accent, #00CAFF);
}

/* ---- Event Form & List (Learning Panel) ---- */

#event-form select,
#event-form input[type="time"],
.event-form select,
.event-form input[type="time"] {
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: rgba(13, 17, 23, 0.6);
  border: 1px solid rgba(0, 202, 255, 0.15);
  border-radius: 8px;
  color: var(--color-text, #e6edf3);
  font-family: var(--font-family, 'Inter', sans-serif);
  font-size: 0.875rem;
  outline: none;
  transition: border-color 0.15s ease;
}

/* Make the native time-picker clock icon visible on dark backgrounds */
#event-form input[type="time"]::-webkit-calendar-picker-indicator,
.event-form input[type="time"]::-webkit-calendar-picker-indicator,
.special-event-row input[type="time"]::-webkit-calendar-picker-indicator {
  filter: invert(0.8) sepia(1) saturate(3) hue-rotate(160deg);
  cursor: pointer;
  opacity: 0.7;
}

#event-form input[type="time"]::-webkit-calendar-picker-indicator:hover,
.event-form input[type="time"]::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
}

#event-form select:focus,
#event-form input[type="time"]:focus,
.event-form select:focus,
.event-form input[type="time"]:focus {
  border-color: rgba(0, 202, 255, 0.5);
}

.event-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.field-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-text-muted, #8b949e);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.field-group select,
.field-group input[type="time"] {
  width: 100%;
}

.devices-row {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.devices-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-muted, #8b949e);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.devices-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.device-checkbox {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  color: var(--color-text, #e6edf3);
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  background: rgba(0, 202, 255, 0.04);
  border: 1px solid rgba(0, 202, 255, 0.1);
  transition: background 0.15s ease, border-color 0.15s ease;
}

.device-checkbox:hover {
  background: rgba(0, 202, 255, 0.1);
  border-color: rgba(0, 202, 255, 0.25);
}

.device-checkbox input[type="checkbox"] {
  accent-color: var(--color-accent, #00CAFF);
  width: 14px;
  height: 14px;
}

.learning-panel-header h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text, #e6edf3);
}

.routine-counter {
  margin: 0 0 0.5rem 0;
  font-size: 0.8rem;
  color: var(--color-accent, #00CAFF);
  font-weight: 500;
}

.event-group {
  margin-bottom: 0.5rem;
}

.event-group-title {
  margin: 0 0 0.3rem 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-accent, #00CAFF);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.event-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.6rem;
  margin-bottom: 0.3rem;
  background: rgba(0, 202, 255, 0.04);
  border: 1px solid rgba(0, 202, 255, 0.1);
  border-radius: 6px;
  transition: background 0.15s ease;
}

.event-item:hover {
  background: rgba(0, 202, 255, 0.08);
}

.event-item-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}

.event-time {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-accent, #00CAFF);
  font-family: 'Inter', monospace;
}

.event-type {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text, #e6edf3);
}

.event-room {
  font-size: 0.7rem;
  color: var(--color-text-muted, #8b949e);
}

.event-devices {
  font-size: 0.65rem;
  color: var(--color-text-muted, #8b949e);
  opacity: 0.8;
}

.event-remove-btn {
  background: none;
  border: none;
  color: var(--color-text-muted, #8b949e);
  cursor: pointer;
  font-size: 0.8rem;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  transition: color 0.15s ease, background 0.15s ease;
  flex-shrink: 0;
}

.event-remove-btn:hover {
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.1);
}

.event-list-empty {
  text-align: center;
  color: var(--color-text-muted, #8b949e);
  font-size: 0.8rem;
  padding: 1rem 0;
  margin: 0;
}

.event-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.event-label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text, #e6edf3);
}

.event-meta {
  font-size: 0.75rem;
  color: var(--color-text-muted, #8b949e);
}

.empty-state {
  text-align: center;
  color: var(--color-text-muted, #8b949e);
  font-size: 0.8rem;
  padding: 1rem 0;
}

/* ---- Event Log Entries ---- */

.event-log-header {
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.event-log-title {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-accent, #00CAFF);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.event-log-close {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid rgba(0, 202, 255, 0.15);
  background: rgba(13, 17, 23, 0.6);
  color: var(--color-text-muted, #8b949e);
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.event-log-close:hover {
  background: rgba(255, 107, 107, 0.12);
  color: #ff6b6b;
  border-color: rgba(255, 107, 107, 0.4);
}

.event-log-entries {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: calc(100vh - 12rem);
  overflow-y: auto;
  padding-right: 0.25rem;
}

.event-log-entries::-webkit-scrollbar {
  width: 4px;
}

.event-log-entries::-webkit-scrollbar-track {
  background: transparent;
}

.event-log-entries::-webkit-scrollbar-thumb {
  background: rgba(0, 202, 255, 0.2);
  border-radius: 2px;
}

.event-log-entry {
  background: rgba(0, 202, 255, 0.04);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(0, 202, 255, 0.08);
  border-left: 3px solid var(--color-accent, #00CAFF);
  border-radius: 8px;
  padding: 0.6rem 0.75rem;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.event-log-entry:hover {
  background: rgba(0, 202, 255, 0.08);
}

.event-log-entry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.3rem;
}

.event-log-time {
  font-family: 'Inter', monospace;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-accent, #00CAFF);
  letter-spacing: 0.03em;
}

.event-log-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.event-log-stage {
  font-size: 0.6rem;
  font-weight: 600;
  color: var(--color-text-muted, #8b949e);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: rgba(255, 255, 255, 0.05);
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}

.event-log-tier {
  font-size: 0.6rem;
  font-weight: 500;
  color: var(--color-accent, #00CAFF);
  background: rgba(0, 202, 255, 0.1);
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}

.event-log-confidence {
  font-size: 0.6rem;
  font-weight: 500;
  color: #00FF88;
  background: rgba(0, 255, 136, 0.08);
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}

.event-log-entry-action {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.2rem;
}

.event-log-emoji {
  font-size: 0.85rem;
  line-height: 1;
}

.event-log-action-name {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text, #e6edf3);
}

.event-log-device {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-text-muted, #8b949e);
  margin-bottom: 0.2rem;
}

.event-log-reasoning {
  font-size: 0.7rem;
  color: var(--color-text-muted, #8b949e);
  opacity: 0.8;
  line-height: 1.35;
}

/* Event Log Badge Row and Override */
.event-log-badge-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.4rem;
  gap: 0.5rem;
}

.event-log-type-badge {
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #ffffff;
  background: #00CAFF;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  white-space: nowrap;
}

.event-log-override-btn {
  font-family: var(--font-family, 'Inter', sans-serif);
  font-size: 0.6rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  background: rgba(255, 75, 75, 0.1);
  border: 1px solid rgba(255, 75, 75, 0.3);
  border-radius: 4px;
  color: #ff6b6b;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
  outline: none;
}

.event-log-override-btn:hover {
  background: rgba(255, 75, 75, 0.2);
  border-color: rgba(255, 75, 75, 0.5);
}

.event-log-override-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: rgba(255, 75, 75, 0.05);
}

/* Overridden entry strikethrough */
.event-log-entry--overridden .event-log-action-name,
.event-log-entry--overridden .event-log-device,
.event-log-entry--overridden .event-log-reasoning {
  text-decoration: line-through;
  opacity: 0.5;
}

.event-log-entry--overridden {
  opacity: 0.6;
  border-left-color: rgba(255, 75, 75, 0.4) !important;
}

/* ---- Responsive Considerations ---- */

@media (max-width: 1024px) {
  #learning-phase {
    width: 40%;
  }

  [id="3d-container"] {
    left: 40%;
    width: 60%;
  }

  #event-log-panel {
    width: 260px;
  }

  #trust-gauges {
    width: 200px;
  }
}

@media (max-width: 768px) {
  #learning-phase {
    width: 100%;
    height: 50%;
    top: auto;
    bottom: 0;
    transform: translateY(0);
  }

  #learning-phase.hidden {
    transform: translateY(100%);
  }

  [id="3d-container"] {
    left: 0;
    width: 100%;
    height: 50%;
  }

  #event-log-panel {
    width: 100%;
    max-height: 40vh;
    top: auto;
    bottom: 5rem;
    right: 0;
    border-radius: 12px 12px 0 0;
  }

  #trust-gauges {
    width: 100%;
    max-height: 30vh;
    top: 0;
    left: 0;
    border-radius: 0 0 12px 12px;
  }

  #timeline-panel {
    width: 95%;
  }
}

/* ---- CSV Upload & Prediction (Learning Panel) ---- */

.csv-upload-section {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border, rgba(0, 202, 255, 0.15));
}

.csv-upload-section h4 {
  margin: 0 0 0.5rem 0;
}

.csv-help {
  font-size: 0.85rem;
  color: var(--color-text-muted, rgba(230, 237, 243, 0.65));
  margin: 0 0 0.5rem 0;
}

.csv-format {
  font-size: 0.8rem;
  margin-bottom: 0.75rem;
  color: var(--color-text-muted, rgba(230, 237, 243, 0.7));
}

.csv-format summary {
  cursor: pointer;
  color: #00CAFF;
  user-select: none;
}

.csv-format ul {
  margin: 0.5rem 0;
  padding-left: 1.1rem;
}

.csv-format code,
.csv-example {
  background: rgba(0, 202, 255, 0.08);
  border-radius: 4px;
  padding: 0 0.25rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.csv-example {
  display: block;
  padding: 0.6rem 0.75rem;
  margin-top: 0.5rem;
  overflow-x: auto;
  white-space: pre;
  font-size: 0.75rem;
  line-height: 1.4;
}

.csv-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.csv-controls input[type="file"] {
  font-size: 0.8rem;
  color: var(--color-text-muted, rgba(230, 237, 243, 0.8));
  flex: 1 1 180px;
}

.btn-ghost {
  background: transparent;
  color: #00CAFF;
  border: 1px solid rgba(0, 202, 255, 0.4);
  border-radius: var(--border-radius, 8px);
  padding: 0.5rem 0.9rem;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}

.btn-ghost:hover {
  background: rgba(0, 202, 255, 0.1);
  transform: translateY(-1px);
}

.csv-status {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  min-height: 1.2em;
}

.csv-status ul {
  margin: 0.4rem 0 0 0;
  padding-left: 1.1rem;
}

.csv-status-info {
  color: var(--color-text-muted, rgba(230, 237, 243, 0.7));
}

.csv-status-success {
  color: #3fb950;
}

.csv-status-error {
  color: #f85149;
}

/* ---- Learned routines list ---- */

.routines-heading {
  margin: 1.1rem 0 0.5rem 0;
  font-size: 0.9rem;
  color: var(--color-text, #e6edf3);
}

.event-confidence {
  flex-shrink: 0;
  font-size: 0.65rem;
  font-weight: 600;
  color: #3fb950;
  background: rgba(63, 185, 80, 0.12);
  border-radius: 4px;
  padding: 0.1rem 0.35rem;
}

.csv-sample-link {
  display: inline-block;
  margin-top: 0.5rem;
  padding: 0;
  background: none;
  border: none;
  color: #00CAFF;
  font-size: 0.8rem;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.csv-sample-link:hover {
  color: #5fd9ff;
}
PANELSCSS_EOF

echo ""
echo "==> Source updated. Rebuild and redeploy the frontend:"
echo "      npm install      # only if node_modules is missing"
echo "      npm run build    # produces dist/  (serve this directory)"
echo ""
echo "Tip: point the frontend at your AWS backend before building so the"
echo "     CSV is analyzed by Amazon Bedrock (real mode):"
echo "      echo VITE_API_BASE_URL=https://<your-api-gateway-url> >> .env"
echo "      echo VITE_API_PREFIX=                                 >> .env"

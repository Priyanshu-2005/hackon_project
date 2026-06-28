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

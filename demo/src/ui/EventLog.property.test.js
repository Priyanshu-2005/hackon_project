// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fc from 'fast-check';
import { EventLog } from './EventLog.js';

/**
 * Property-Based Tests for EventLog entries.
 *
 * **Validates: Requirements 8.1**
 *
 * Property 10: Event log entries contain required fields — every entry
 * passed to EventLog has time, action, device, reasoning, and type.
 * When a proactive action triggers at its scheduled time, the Event_Log
 * SHALL display an entry with the action name, target device, reasoning
 * summary, and timestamp.
 */

function setupDOM() {
  document.body.innerHTML = `
    <div id="event-log-panel"></div>
  `;
}

function createMockStateStore() {
  const listeners = new Map();
  return {
    on(key, callback) {
      if (!listeners.has(key)) listeners.set(key, new Set());
      listeners.get(key).add(callback);
    },
    emit(key, data) {
      const cbs = listeners.get(key);
      if (cbs) cbs.forEach(cb => cb(data));
    },
  };
}

/** Arbitrary for valid time in minutes (0–1439) */
const arbTime = fc.integer({ min: 0, max: 1439 });

/** Arbitrary for non-empty strings (action, device, reasoning) using alphanumeric + spaces to avoid HTML escaping issues */
const arbNonEmptyString = fc.stringMatching(/^[a-zA-Z0-9 _\-]{1,30}$/).filter(s => s.trim().length > 0);

/** Arbitrary for type strings */
const arbType = fc.oneof(
  fc.constant('ac_precool'),
  fc.constant('geyser_preheat'),
  fc.constant('security_arm'),
  fc.constant('energy_optimization'),
  fc.constant('comfort_lighting'),
  fc.constant('power_cut'),
  fc.string({ minLength: 1, maxLength: 20 }).filter(s => s.trim().length > 0)
);

/** Arbitrary for a complete event entry */
const arbEntry = fc.record({
  time: arbTime,
  action: arbNonEmptyString,
  device: arbNonEmptyString,
  reasoning: arbNonEmptyString,
  type: arbType,
});

describe('EventLog Property Tests - Event Log Entries', () => {
  let eventLog;
  let stateStore;

  beforeEach(() => {
    setupDOM();
    stateStore = createMockStateStore();
    eventLog = new EventLog(stateStore);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('Property 10: Event log entries contain required fields', () => {
    it('for any entry with all required fields, getEntryCount increases by 1 after emission', () => {
      fc.assert(
        fc.property(
          fc.array(arbEntry, { minLength: 1, maxLength: 20 }),
          (entries) => {
            setupDOM();
            const store = createMockStateStore();
            const log = new EventLog(store);

            for (let i = 0; i < entries.length; i++) {
              const countBefore = log.entriesContainer.children.length;
              store.emit('eventlog', entries[i]);
              const countAfter = log.entriesContainer.children.length;
              expect(countAfter).toBe(countBefore + 1);
            }
          }
        ),
        { numRuns: 200 }
      );
    });

    it('for any valid time (0-1439), the rendered timestamp is in [HH:MM] format', () => {
      fc.assert(
        fc.property(
          arbTime,
          arbNonEmptyString,
          arbNonEmptyString,
          arbNonEmptyString,
          arbType,
          (time, action, device, reasoning, type) => {
            setupDOM();
            const store = createMockStateStore();
            const log = new EventLog(store);

            store.emit('eventlog', { time, action, device, reasoning, type });

            const entryEl = log.entriesContainer.querySelector('.event-log-entry');
            const timeEl = entryEl.querySelector('.event-log-time');
            // Verify HH:MM format inside brackets
            expect(timeEl.textContent).toMatch(/^\[\d{2}:\d{2}\]$/);

            // Verify the actual time value is correct
            const h = Math.floor(time / 60).toString().padStart(2, '0');
            const m = Math.floor(time % 60).toString().padStart(2, '0');
            expect(timeEl.textContent).toBe(`[${h}:${m}]`);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('for any string action/device/reasoning, they appear in the rendered HTML', () => {
      fc.assert(
        fc.property(
          arbEntry,
          (entry) => {
            setupDOM();
            const store = createMockStateStore();
            const log = new EventLog(store);

            store.emit('eventlog', entry);

            const entryEl = log.entriesContainer.querySelector('.event-log-entry');

            // Action name appears in the rendered entry
            const actionEl = entryEl.querySelector('.event-log-action-name');
            expect(actionEl.textContent).toBe(entry.action);
            // Device name appears in the rendered entry
            const deviceEl = entryEl.querySelector('.event-log-device');
            expect(deviceEl.textContent).toBe(entry.device);
            // Reasoning text appears in the rendered entry
            const reasoningEl = entryEl.querySelector('.event-log-reasoning');
            expect(reasoningEl.textContent).toBe(entry.reasoning);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('for any valid type string, a border-left accent color is applied', () => {
      fc.assert(
        fc.property(
          arbEntry,
          (entry) => {
            setupDOM();
            const store = createMockStateStore();
            const log = new EventLog(store);

            store.emit('eventlog', entry);

            const entryEl = log.entriesContainer.querySelector('.event-log-entry');
            // Every entry gets a border-left color (the accent styling acts as the badge)
            expect(entryEl.style.borderLeftColor).toBeTruthy();
            expect(entryEl.style.borderLeftColor.length).toBeGreaterThan(0);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('entry ordering is preserved — entries emitted in order appear in order', () => {
      fc.assert(
        fc.property(
          fc.array(arbEntry, { minLength: 2, maxLength: 30 }),
          (entries) => {
            setupDOM();
            const store = createMockStateStore();
            const log = new EventLog(store);

            // Emit all entries in order
            for (const entry of entries) {
              store.emit('eventlog', entry);
            }

            // Verify DOM order matches emission order
            const renderedEntries = log.entriesContainer.querySelectorAll('.event-log-entry');
            expect(renderedEntries.length).toBe(entries.length);

            for (let i = 0; i < entries.length; i++) {
              const actionEl = renderedEntries[i].querySelector('.event-log-action-name');
              expect(actionEl.textContent).toBe(entries[i].action);

              const deviceEl = renderedEntries[i].querySelector('.event-log-device');
              expect(deviceEl.textContent).toBe(entries[i].device);
            }
          }
        ),
        { numRuns: 200 }
      );
    });
  });
});

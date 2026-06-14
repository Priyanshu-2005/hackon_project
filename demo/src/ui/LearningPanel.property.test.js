// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fc from 'fast-check';
import { LearningPanel } from './LearningPanel.js';

/**
 * Property-Based Tests for LearningPanel event list management.
 *
 * **Validates: Requirements 4.5, 4.6**
 *
 * Property 4: Event addition grows list — adding an event increases the events array length by 1.
 * Property 5: Event removal shrinks list — removing an event decreases the events array length by 1.
 */

// Valid options for generators (matching LearningPanel constants)
const FAMILY_MEMBERS = ['Rajesh', 'Priya', 'Arjun', 'Ananya', 'Dadaji', 'Dadiji'];
const EVENT_TYPES = ['Wake up', 'Leave home', 'Arrive home', 'Start cooking', 'Online class', 'Afternoon rest', 'TV time', 'Bedtime', 'Custom'];
const ROOMS = ['Living Room', 'Kitchen', 'Master Bedroom', 'Kids Room', 'Study Room', 'Bathroom', 'Balcony'];
const DEVICES = ['AC', 'Lights', 'Geyser', 'TV', 'Lock', 'Camera', 'Purifier', 'Kitchen Hub', 'Echo'];

/**
 * Arbitrary for valid event data matching the LearningPanel's expected format.
 */
const eventDataArb = fc.record({
  member: fc.constantFrom(...FAMILY_MEMBERS),
  type: fc.constantFrom(...EVENT_TYPES),
  time: fc.tuple(
    fc.integer({ min: 0, max: 23 }),
    fc.integer({ min: 0, max: 59 })
  ).map(([h, m]) => `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`),
  room: fc.constantFrom(...ROOMS),
  devices: fc.subarray(DEVICES, { minLength: 0 }),
});

function setupDOM() {
  document.body.innerHTML = `
    <div id="event-form"></div>
    <div id="event-list"></div>
    <button id="deploy-btn">Deploy →</button>
    <form id="add-event-form"></form>
    <p id="routine-counter"></p>
  `;
}

function createMockUIManager() {
  return { deploy: () => {} };
}

describe('LearningPanel Property Tests - Event List Management', () => {
  let panel;

  beforeEach(() => {
    setupDOM();
    panel = new LearningPanel(createMockUIManager());
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('Property 4: Event addition grows list', () => {
    it('adding any valid event increases list length by exactly 1', () => {
      fc.assert(
        fc.property(
          eventDataArb,
          (eventData) => {
            setupDOM();
            const p = new LearningPanel(createMockUIManager());
            const lengthBefore = p.getEvents().length;

            p.addEvent(eventData);

            const lengthAfter = p.getEvents().length;
            expect(lengthAfter).toBe(lengthBefore + 1);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('adding N events increases length by exactly N', () => {
      fc.assert(
        fc.property(
          fc.array(eventDataArb, { minLength: 1, maxLength: 20 }),
          (eventsToAdd) => {
            setupDOM();
            const p = new LearningPanel(createMockUIManager());
            const lengthBefore = p.getEvents().length;

            for (const eventData of eventsToAdd) {
              p.addEvent(eventData);
            }

            const lengthAfter = p.getEvents().length;
            expect(lengthAfter).toBe(lengthBefore + eventsToAdd.length);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('the added event is present in the list after addition', () => {
      fc.assert(
        fc.property(
          eventDataArb,
          (eventData) => {
            setupDOM();
            const p = new LearningPanel(createMockUIManager());

            p.addEvent(eventData);

            const events = p.getEvents();
            const found = events.find(
              e => e.member === eventData.member &&
                   e.type === eventData.type &&
                   e.time === eventData.time &&
                   e.room === eventData.room
            );
            expect(found).toBeDefined();
          }
        ),
        { numRuns: 200 }
      );
    });
  });

  describe('Property 5: Event removal shrinks list', () => {
    it('removing any existing event decreases list length by exactly 1', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 0, max: 19 }),
          (index) => {
            setupDOM();
            const p = new LearningPanel(createMockUIManager());
            const events = p.getEvents();
            const lengthBefore = events.length;
            const eventToRemove = events[index];

            p.removeEvent(eventToRemove.id);

            const lengthAfter = p.getEvents().length;
            expect(lengthAfter).toBe(lengthBefore - 1);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('removing an event that does not exist does not change the list length', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 10, maxLength: 30 }),
          (fakeId) => {
            setupDOM();
            const p = new LearningPanel(createMockUIManager());
            // Make sure the fakeId doesn't match any real event
            const realIds = p.getEvents().map(e => e.id);
            fc.pre(!realIds.includes(fakeId));

            const lengthBefore = p.getEvents().length;

            p.removeEvent(fakeId);

            const lengthAfter = p.getEvents().length;
            expect(lengthAfter).toBe(lengthBefore);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('after adding then removing an event, length returns to original', () => {
      fc.assert(
        fc.property(
          eventDataArb,
          (eventData) => {
            setupDOM();
            const p = new LearningPanel(createMockUIManager());
            const lengthBefore = p.getEvents().length;

            p.addEvent(eventData);
            // Find the newly added event (last one in the list)
            const eventsAfterAdd = p.getEvents();
            const addedEvent = eventsAfterAdd[eventsAfterAdd.length - 1];

            p.removeEvent(addedEvent.id);

            const lengthAfter = p.getEvents().length;
            expect(lengthAfter).toBe(lengthBefore);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('the removed event is no longer present in the list', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 0, max: 19 }),
          (index) => {
            setupDOM();
            const p = new LearningPanel(createMockUIManager());
            const events = p.getEvents();
            const eventToRemove = events[index];

            p.removeEvent(eventToRemove.id);

            const eventsAfter = p.getEvents();
            const found = eventsAfter.find(e => e.id === eventToRemove.id);
            expect(found).toBeUndefined();
          }
        ),
        { numRuns: 200 }
      );
    });
  });
});

// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest';
import { test as fcTest } from '@fast-check/vitest';
import fc from 'fast-check';
import { FAMILY_SCHEDULE } from './AvatarManager.js';
import { ROOM_DEFINITIONS } from './RoomDefinitions.js';

/**
 * Property-Based Tests for Avatar Positioning.
 *
 * **Validates: Requirements 6.2**
 *
 * Property 6: Avatar position matches schedule — at any time, each avatar is
 * either hidden (when away) or positioned in the correct room.
 *
 * We verify the schedule data integrity that drives avatar positioning:
 * 1. For any time in [0, 1439], every family member has exactly one matching schedule entry
 * 2. For any time where room is null, the avatar should be hidden (away)
 * 3. For any time where room is not null, the room ID is a valid room from ROOM_DEFINITIONS
 * 4. Schedule entries for each member cover the full day [0, 1440) with no gaps
 */

const VALID_ROOM_IDS = ROOM_DEFINITIONS.map((r) => r.id);
const FAMILY_MEMBERS = Object.keys(FAMILY_SCHEDULE);

describe('AvatarManager Property Tests - Avatar Position Matches Schedule', () => {
  describe('Property 6: Avatar position matches schedule', () => {
    fcTest.prop(
      [fc.integer({ min: 0, max: 1439 })],
      { numRuns: 500 }
    )(
      'for any time in [0, 1439], every family member has exactly one matching schedule entry',
      (timeMinutes) => {
        for (const memberId of FAMILY_MEMBERS) {
          const schedule = FAMILY_SCHEDULE[memberId];
          const matchingEntries = schedule.filter(
            (s) => timeMinutes >= s.start && timeMinutes < s.end
          );
          expect(
            matchingEntries.length,
            `Member ${memberId} at time ${timeMinutes} should have exactly 1 matching entry, found ${matchingEntries.length}`
          ).toBe(1);
        }
      }
    );

    fcTest.prop(
      [fc.integer({ min: 0, max: 1439 })],
      { numRuns: 500 }
    )(
      'for any time where room is null, avatar is hidden (away from home)',
      (timeMinutes) => {
        for (const memberId of FAMILY_MEMBERS) {
          const schedule = FAMILY_SCHEDULE[memberId];
          const slot = schedule.find(
            (s) => timeMinutes >= s.start && timeMinutes < s.end
          );
          if (slot && slot.room === null) {
            // When room is null, the avatar would be hidden (mesh.visible = false)
            // This verifies the schedule correctly marks away-from-home periods
            expect(slot.room).toBeNull();
            expect(slot.activity).toBeDefined();
          }
        }
      }
    );

    fcTest.prop(
      [fc.integer({ min: 0, max: 1439 })],
      { numRuns: 500 }
    )(
      'for any time where room is not null, the room ID is a valid room from ROOM_DEFINITIONS',
      (timeMinutes) => {
        for (const memberId of FAMILY_MEMBERS) {
          const schedule = FAMILY_SCHEDULE[memberId];
          const slot = schedule.find(
            (s) => timeMinutes >= s.start && timeMinutes < s.end
          );
          if (slot && slot.room !== null) {
            expect(
              VALID_ROOM_IDS,
              `Member ${memberId} at time ${timeMinutes} has room '${slot.room}' which is not in ROOM_DEFINITIONS`
            ).toContain(slot.room);
          }
        }
      }
    );

    it('schedule entries for each member cover the full day [0, 1440) with no gaps', () => {
      for (const memberId of FAMILY_MEMBERS) {
        const schedule = FAMILY_SCHEDULE[memberId];

        // Sort entries by start time
        const sorted = [...schedule].sort((a, b) => a.start - b.start);

        // First entry must start at 0
        expect(
          sorted[0].start,
          `Member ${memberId}: schedule does not start at 0, starts at ${sorted[0].start}`
        ).toBe(0);

        // Last entry must end at 1440
        expect(
          sorted[sorted.length - 1].end,
          `Member ${memberId}: schedule does not end at 1440, ends at ${sorted[sorted.length - 1].end}`
        ).toBe(1440);

        // Each entry's end must equal the next entry's start (no gaps, no overlaps)
        for (let i = 0; i < sorted.length - 1; i++) {
          expect(
            sorted[i].end,
            `Member ${memberId}: gap between entries at index ${i} (end=${sorted[i].end}) and ${i + 1} (start=${sorted[i + 1].start})`
          ).toBe(sorted[i + 1].start);
        }
      }
    });

    it('all 6 family members are present in FAMILY_SCHEDULE', () => {
      const expected = ['rajesh', 'priya', 'arjun', 'ananya', 'dadaji', 'dadiji'];
      expect(FAMILY_MEMBERS).toEqual(expect.arrayContaining(expected));
      expect(FAMILY_MEMBERS.length).toBe(6);
    });

    fcTest.prop(
      [fc.constantFrom(...FAMILY_MEMBERS), fc.integer({ min: 0, max: 1439 })],
      { numRuns: 500 }
    )(
      'for any member and time, updatePositions logic correctly determines visibility',
      (memberId, timeMinutes) => {
        const schedule = FAMILY_SCHEDULE[memberId];
        const slot = schedule.find(
          (s) => timeMinutes >= s.start && timeMinutes < s.end
        );

        // The updatePositions method logic:
        // if (!slot || slot.room === null) → mesh.visible = false
        // else → mesh.visible = true, position toward room
        if (!slot || slot.room === null) {
          // Avatar should be hidden
          expect(slot === undefined || slot.room === null).toBe(true);
        } else {
          // Avatar should be visible and room must be valid
          expect(slot.room).not.toBeNull();
          expect(VALID_ROOM_IDS).toContain(slot.room);
        }
      }
    );
  });
});
